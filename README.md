# longqc.nf

## QUICK START
```
nextflow run https://github.com/grpiccoli/longqc.nf [-profile <{standard}|scrum>] --i_bam ccs.bam
```

### OPTIONS:
| Options   | Default Value | Description
| --------- | ------------- | ------------------------------------------------
| -profile  | standard      | sets local executor to local (standard) or slurm (rapoi)  
| --i_f     | REQUIRED      | path to input pacbio fasta or fastq file  
| --s       | 4W            | sample name  
| --i       | 4G            | Give index size for minimap2 (-I) in bp. Reduce when running on a small memory machine  
| --n       | 1             | Number of samples  
| --t       | false|true    | When true IsoSeq transcripts otherwise HiFi  

## Copyright and license
[minimap2](https://github.com/lh3/minimap2) was originally developed by Heng Li and licensed under MIT. [mix'EM](https://github.com/sseemayer/mixem) was developed by Stefan Seemayer and licensed under MIT. Yoshinori slightly modified their codes.
The [LongQC](https://github.com/yfukasawa/LongQC) codes are licensed under MIT.