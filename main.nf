#!/usr/bin/env nextflow
Channel.fromPath("$params.i_f", type: 'file')
.buffer(size:1)
.set{
    ref;
}

process longqc {
	tag "longqc.$r"
    publishDir "$params.o"
    container "$params.c"

    input:
    file r from ref

    output:
    file "longqc/*" into longqc

    script:
    """
    /opt/conda/bin/python /LongQC-1.2.0b/longQC.py \
    sampleqc \
    -x $params.x \
    -o longqc \
    $r
    """
}