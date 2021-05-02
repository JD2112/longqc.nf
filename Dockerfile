# build minimap2-coverage
FROM continuumio/miniconda3:4.7.12-alpine
### LABELS ###
LABEL Guillermo R. Piccoli <grpiccoli@gmail.com>
LABEL base_image="miniconda3"
LABEL software="LongQC docker"
LABEL software.version="1.2"

### ENV VARS ###
ENV BIN=/usr/local/bin

RUN apk add --no-cache \
bash=5.1.0-r0 \
tzdata=2021a-r0 \
build-base=0.5-r2 \
libc-dev=0.7.2-r3 \
zlib-dev=1.2.11-r3 \
wget=1.21.1-r1 \
argp-standalone=1.3-r4

RUN wget -qO- https://github.com/yfukasawa/LongQC/archive/refs/tags/1.2.0b.tar.gz | tar zxvf -
RUN cd LongQC-1.2.0b/minimap2-coverage && \
sed -i \
-e '3{s;$;-I/usr/include -L/usr/lib;}' \
-e '7{s/$/ -largp/}' \
Makefile && \
make

RUN conda update -n base -c defaults conda

# python 3.9
RUN conda install -y \
python=3.9 \
numpy=1.20.1 \
pandas=1.2.4 \
scipy=1.6.2 \
jinja2=2.11.3 \
h5py=2.10.0 \
matplotlib=3.3.4 \
scikit-learn=0.24.1

RUN conda config --add channels defaults && \
conda config --add channels conda-forge && \
conda config --add channels bioconda

RUN conda install -y -c bioconda \
edlib=1.2.3 \
pysam=0.16.0.1 \
python-edlib=1.3.8.post2

#cleaning
RUN apk del tzdata build-base wget

WORKDIR "/root/LongQC-1.2.0b"

ENTRYPOINT ["python3.9 longQC.py"]