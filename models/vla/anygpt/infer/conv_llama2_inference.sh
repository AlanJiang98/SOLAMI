#!/bin/bash



OUTPUT_DIR=(
    "SOLAMI/models/vla/infer_output/llama2-dlp-motiongpt-retrieval-final-0"
    "SOLAMI/models/vla/infer_output/llama2-dlp-motiongpt-retrieval-final-2"
    "SOLAMI/models/vla/infer_output/llama2-dlp-motiongpt-retrieval-final-3"
    "SOLAMI/models/vla/infer_output/llama2-dlp-motiongpt-retrieval-final-4"
)
for i in "${!OUTPUT_DIR[@]}"; do
    CUDA_VISIBLE_DEVICES=6,7 python conv_llama2_inference.py --part 0 --period 1  --output_dir ${OUTPUT_DIR[$i]} --method 'dlp+motiongpt+retrieval' &
    wait
done

echo "All processes have finished."