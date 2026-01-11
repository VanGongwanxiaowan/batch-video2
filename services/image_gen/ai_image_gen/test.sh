cd /data2/home_back/gujiaxin/work/batchshort1/ai_image_gen
conda activate batchshort
export PYTHONPATH=.
python consumer_worker/kafka_monitor.py 


export CUDA_VISIBLE_DEVICES=-1
python consumer_worker/worker.py 
