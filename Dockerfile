# build minimap2-coverage
FROM continuumio/miniconda3:4.9.2-alpine
### LABELS ###
LABEL Guillermo R. Piccoli <grpiccoli@gmail.com>
LABEL base_image="miniconda3-alpine"
LABEL software="LongQC docker"
LABEL software.version="1.2"

### DEFAULTS ####
RUN apk add --no-cache \
bash=5.0.17-r0 \
build-base=0.5-r2 \
libc-dev=0.7.2-r3 \
zlib-dev=1.2.11-r3 \
wget=1.20.3-r1 \
argp-standalone=1.3-r4 \
zlib=1.2.11-r3

## set bash as default for root ##
RUN sed -i '1{s;/ash;/bash;}' /etc/passwd

## install LongQC ##
RUN wget -qO- https://github.com/yfukasawa/LongQC/archive/refs/tags/1.2.0b.tar.gz | \
tar zxvf - && \
cd LongQC-1.2.0b && \
sed -i \
-e '1{s;^;#!/opt/conda/bin/python\n;}' \
longQC.py && \
mv longQC.py longQC && \
chmod +x longQC && \
cd minimap2-coverage && \
sed -i \
-e '3{s;$;-I/usr/include -L/usr/lib;}' \
-e '7{s/$/ -largp/}' \
Makefile && \
make && \
cd .. && \
mv * /usr/bin

## install conda requirements ##
RUN conda install -y \
python=3.9 \
numpy=1.20.1 \
pandas=1.2.4 \
scipy=1.6.2 \
jinja2=2.11.3 \
h5py=2.10.0 \
matplotlib=3.3.4 \
scikit-learn=0.24.1 && \
conda config --add channels conda-forge && \
conda config --add channels bioconda && \
conda install -y -c bioconda \
edlib=1.2.3 \
pysam=0.16.0.1 \
python-edlib=1.3.8.post2

#cleaning
RUN apk del build-base wget zlib-dev

ENTRYPOINT ["longQC"]