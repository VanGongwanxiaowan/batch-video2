import concurrent.futures
import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

from clients.tts_seedvc_client import VoiceSynthesisClient, edge_lang_voice_map
from opencc import OpenCC
from pydub import AudioSegment

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.logging_config import setup_logging

# 配置日志
logger = setup_logging("worker.clients.batch_synthesis", log_to_file=False)
def _synthesize_segment_task(
    index: int,
    text: str,
    client: VoiceSynthesisClient,
    reference_audio_path: str,
    voice: str,
    volume: int,
    speech_rate: int,
    pitch_rate: int,
    tts_type: Optional[str],
    diffusion_steps: int,
    length_adjust: float,
    inference_cfg_rate: float,
    job_id: int
) -> Tuple[Optional[AudioSegment], str, int]:
    """Helper function to synthesize a single audio segment in a separate thread with retries."""
    from core.config.constants import RetryConfig
    
    temp_audio_file = f"{job_id}_temp_segment_{index}.wav"
    max_retries = RetryConfig.MAX_RETRIES_TTS
    origin_text = text
    # 繁体转简体
    if "zh-" in voice:
        text = OpenCC('t2s').convert(text)

    new_text = text.replace("没", '梅')

    for attempt in range(max_retries):
        logger.debug(f"Synthesizing segment {index+1}: '{text}' (Attempt {attempt + 1}/{max_retries})")
        success = client.synthesize_voice(
            text=new_text,
            audio_file_path=reference_audio_path,
            voice=voice,
            output_file=temp_audio_file,
            volume=volume,
            speech_rate=speech_rate,
            pitch_rate=pitch_rate,
            tts_type=tts_type,
            diffusion_steps=diffusion_steps,
            length_adjust=length_adjust,
            inference_cfg_rate=inference_cfg_rate,
        )
        if success:
            segment_audio = AudioSegment.from_wav(temp_audio_file)
            os.remove(temp_audio_file) # Clean up immediately after loading
            logger.info(f"Successfully synthesized segment {index+1}: '{text}'")
            return segment_audio, text, index
        else:
            logger.warning(f"Failed to synthesize text for segment {index+1}: '{text}' on attempt {attempt + 1}.")
            if os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)
            from core.config.constants import RetryConfig
            
            if attempt < max_retries - 1:
                time.sleep(RetryConfig.RETRY_SLEEP_MS / 1000)  # 使用配置的重试间隔
    
    logger.error(f"Failed to synthesize text for segment {index+1}: '{text}' after {max_retries} attempts.")
    return None, origin_text, index

def batch_synthesize_and_generate_srt(
    text_list: List[str],
    reference_audio_path: str,
    language: str,
    output_base_name: str,
    base_url: str = "http://127.0.0.1:8007",
    sleep_ms: int = 300,
    volume: int = 50,
    speech_rate: int = 0,
    pitch_rate: int = 0,
    tts_type: Optional[str] = 'edge',
    diffusion_steps: int = 50,
    length_adjust: float = 1.0,
    inference_cfg_rate: float = 0.7,
    max_workers: int = None,  # 如果为None，使用WorkerConfig.DEFAULT_MAX_WORKERS
    job_id: int = 0
) -> Optional[str]:
    """
    Synthesizes a list of texts, combines them with silence, and generates an SRT file.

    Args:
        text_list: A list of strings to synthesize.
        reference_audio_path: Path to the reference audio file for voice cloning.
        language: The language of the text (e.g., '英语', '中文').
        output_base_name: Base name for the output audio and SRT files (e.g., 'output_audio').
                          The final files will be output_base_name.wav and output_base_name.srt.
        base_url: Base URL for the voice synthesis API.
        sleep_ms: Duration of silence to insert between audio segments in milliseconds.
        volume: Volume level (0-100).
        speech_rate: Speech rate adjustment.
        pitch_rate: Pitch rate adjustment.
        tts_type: Type of TTS engine ('edge' or 'aly').
        diffusion_steps: Diffusion steps for 'aly' TTS.
        length_adjust: Length adjustment for 'aly' TTS.
        inference_cfg_rate: Inference config rate for 'aly' TTS.

    Returns:
        Optional[str]: Path to the generated SRT file if successful, None otherwise.
    """
    client = VoiceSynthesisClient(base_url)
    voice = language
    if not voice:
        logger.error(f"Error: Language '{language}' not found in voice map.")
        return None

    output_dir = os.path.dirname(output_base_name)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Use a dictionary to store results, keyed by original index to maintain order
    results_map = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(
            _synthesize_segment_task,
            i, text, client, reference_audio_path, voice, volume, speech_rate,
            pitch_rate, tts_type, diffusion_steps, length_adjust, inference_cfg_rate, job_id
        ) for i, text in enumerate(text_list)]

        for future in concurrent.futures.as_completed(futures):
            segment_audio, text_content, original_index = future.result()
            if segment_audio:
                results_map[original_index] = (segment_audio, text_content)
            else:
                logger.error(f"Synthesis failed for segment at index {original_index}: '{text_content}'")
                # Clean up any temporary files that might still exist from failed tasks
                for j in range(len(text_list)):
                    temp_file = f"{job_id}_temp_segment_{j}.wav"
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                return None # Exit if any segment fails

    combined_audio = AudioSegment.empty()
    srt_entries = []
    current_time_ms = 0

    # Process results in original order
    for i in range(len(text_list)):
        segment_audio, text = results_map[i]
        
        segment_duration_ms = len(segment_audio)

        start_time_srt = format_time(current_time_ms)
        end_time_srt = format_time(current_time_ms + segment_duration_ms)
        srt_entries.append(
            f"{i + 1}\n"
            f"{start_time_srt} --> {end_time_srt}\n"
            f"{text}\n"
        )

        combined_audio += segment_audio
        current_time_ms += segment_duration_ms

        # Add sleep/silence if not the last segment
        if i < len(text_list) - 1:
            silence = AudioSegment.silent(duration=sleep_ms)
            combined_audio += silence
            current_time_ms += sleep_ms
        
    output_audio_path = f"{output_base_name}.wav"
    output_srt_path = f"{output_base_name}.srt"

    logger.info(f"Exporting combined audio to {output_audio_path}")
    combined_audio.export(output_audio_path, format="wav")

    logger.info(f"Generating SRT file to {output_srt_path}")
    with open(output_srt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(srt_entries))

    logger.info("Batch synthesis and SRT generation complete.")
    return output_srt_path

def format_time(ms: int) -> str:
    """Formats milliseconds into SRT time format (HH:MM:SS,mmm).
    
    Note: 此函数已使用core.utils.time_formatter中的统一实现
    """
    from core.utils.time_formatter import format_time_ms_to_srt
    return format_time_ms_to_srt(ms)

if __name__ == '__main__':

    texts_to_synthesize = ['您有没有想过', '当自己老了', '病了', '最需要依靠的时候', '曾经最疼爱的儿女', '会不会首先想到的是您的财产', '而不是您的安危', '都说养儿防老', '可有时候', '这份期望会不会变成一把刺向我们心口的刀', '今天', '我们要认识一位叫李建国的老人', '他勤勤恳恳一辈子', '把所有心血都倾注在家庭和儿女身上', '然而', '老伴的突然离世', '像一块巨石投入平静的湖面', '激起的涟漪', '却让他看清了亲情在现实面前的脆弱', '老伴的追悼会刚结束', '儿女们不是先安慰他如何度过悲伤', '而是迫不及待地商量起了“身后事”', '那一刻', '李建国的心', '比冬日的寒冰还要冷', '但谁能想到', '老伴生前看似不经意的一个“馊主意”', '竟成了他晚年对抗风雨', '守护尊严最坚实的盾牌', '人到晚年', '究竟什么才是我们真正的依靠', '金钱和亲情', '孰轻孰重', '今天', '让我们一起倾听李建国老人的心声', '看看他是如何在风雨飘摇中', '为自己撑起一片晴空']

    

    reference_audio = 'assrts/ref.wav' 
    # Ensure the reference audio file exists for the example to run
    if not os.path.exists(reference_audio):
        logger.error(f"Error: Reference audio file '{reference_audio}' not found.")
        logger.error("Please create or provide a valid path to a WAV file for voice cloning.")
    else:
        output_name = 'tts_seedvc_server/combined_output'
        srt_file = batch_synthesize_and_generate_srt(
            text_list=texts_to_synthesize,
            reference_audio_path=reference_audio,
            language='中文', 
            output_base_name=output_name,
            base_url='http://127.0.0.1:8007', # Adjust if your server is on a different address/port
            sleep_ms=300,
            speech_rate=0.91,
            tts_type='edge', # or 'aly'
            job_id=0,
        )

        if srt_file:
            logger.info(f"SRT file generated at: {srt_file}")
            logger.info(f"Combined audio at: {output_name}.wav")
        else:
            logger.error("Batch synthesis failed.")