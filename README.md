[![longqc_docker](https://github.com/JD2112/longqc.nf/actions/workflows/docker-image.yml/badge.svg)](https://github.com/JD2112/longqc.nf/actions/workflows/docker-image.yml)
# Direct run from command line after conda installation
```
python3 longQC.py sampleqc -x ont-rapid \
-o /mnt/SD2/NanoMeth/QC_Results/LongQC/TB190830 \
/mnt/SD2/NanoMeth/guppy_result/TB190830/TB190830.fastq \
-p 24
```
# Changes
1. nextflow config file changed - requires a config file for other methods
2. main file script changed to python version 3.

# <Original README from grpiccoli>
# longqc.nf

## QUICK START - BASIC USAGE
```
nextflow run https://github.com/grpiccoli/longqc.nf --i_f <sample>.bam
```

### OPTIONS:

| Options       | Default Value                      | Description
| ------------- | ---------------------------------- | ---------------------------------------
| --i_f         | REQUIRED/NULL                      | path to input bam, fastx file  
| --a           | sampleqc -x pb-hifi -o longqc -m 2 | longqc arguments  
| --o           | output/seq_quality                 | output directory    
| **Advanced Opts** |                         |
| --m           | 24.GB                   | RAM memory allocation  
| --p           | 12                      | CPU core allocation  
| --c           | grpiccoli/longqc:latest | longqc container url:tag
| **HPC Opts**      |                         |
| --e           | local                   | nextflow executor (slurm, local, etc)  
| --q           | bigmem                  | queue/partition name  
| --t           | 4h                      | max execution time  

## Copyright and license
[minimap2](https://github.com/lh3/minimap2) was originally developed by Heng Li and licensed under MIT. [mix'EM](https://github.com/sseemayer/mixem) was developed by Stefan Seemayer and licensed under MIT. Yoshinori slightly modified their codes.
The [LongQC](https://github.com/yfukasawa/LongQC) codes are licensed under MIT.
