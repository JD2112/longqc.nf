#!/usr/bin/env nextflow
Channel.fromPath("$params.i_f", type: 'file')
.buffer(size:1)
.set{
    ref;
}

process longqc {
	tag "pb_assembly.$x"
    publishDir "$params.out_asm"
    container "grpiccoli/longqc:latest"

    input:
    file r from ref

    output:
    file "*fasta" into longqc

    script:
    """
    if $params.t; then
        t="-t"
    fi
    mem=`echo "$task.memory" | sed 's/[^0-9]*//g'`
    mem=`expr \$mem / $task.cpus`
    longQC.py sampleqc \
    -d \
    -p $task.cpus \
    -m \$mem \
    -x $params.x \
    -o longqc $r \
    -i $params.i \
    -s $params.s \
    -n $params.n \
    \$t
    """
}