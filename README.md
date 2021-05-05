# longqc.nf

## QUICK START - BASIC USAGE
```
nextflow run https://github.com/grpiccoli/longqc.nf --i_f ccs.bam
```

### OPTIONS:
| Options       | Default Value                      | Description
| ------------- | ---------------------------------- | ---------------------------------------
| --i_f         | REQUIRED/NULL                      | path to input bam, fastx file  
| --a           | sampleqc -x pb-hifi -o longqc -m 2 | longqc arguments  
| --o           | output/seq_quality                 | output directory    

| Advanced Opts |                         |
| ------------- | ----------------------- | ---------------------------------------
| --m           | 24.GB                   | RAM memory allocation  
| --p           | 12                      | CPU core allocation  
| --c           | grpiccoli/longqc:latest | longqc container url:tag    

| HPC Opts      |                         |
| ------------- | ----------------------- | ---------------------------------------
| --e           | local                   | nextflow executor (slurm, local, etc)  
| --q           | bigmem                  | queue/partition name  
| --t           | 4h                      | max execution time  

## Copyright and license
[minimap2](https://github.com/lh3/minimap2) was originally developed by Heng Li and licensed under MIT. [mix'EM](https://github.com/sseemayer/mixem) was developed by Stefan Seemayer and licensed under MIT. Yoshinori slightly modified their codes.
The [LongQC](https://github.com/yfukasawa/LongQC) codes are licensed under MIT.