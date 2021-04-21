# build minimap2-coverage
FROM continuumio/miniconda3:4.9.2
### MAINTAINER ###
LABEL Guillermo R. Piccoli <grpiccoli@gmail.com>

RUN apt-get clean all && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y  \
    git=1:2.20.1-2+deb10u3 \
    build-essential=12.6 \
    libc6-dev=2.28-10 \
    zlib1g-dev=1:1.2.11.dfsg-1 && \
    apt-get clean && \
    apt-get purge

### ENV VARS ###
ENV USER user
ENV HOME /home/${USER}

### LABELS ###
LABEL base_image="miniconda3"
LABEL software="LongQC docker"
LABEL software.version="1.2"

# add a general user account
RUN useradd -m ${USER}
# define a password for user
RUN echo "${USER}:test_pass" | chpasswd

ADD https://api.github.com/repos/yfukasawa/longqc/git/refs/heads/minimap2_update version.json
RUN BIN=/usr/local/bin
RUN wget -qO- https://github.com/yfukasawa/LongQC/archive/refs/tags/1.2.0b.tar.gz | tar zxvf -
RUN cd LongQC-1.2.0b
RUN sed -i '1s;^;#!/opt/conda/bin/python3.8\n;' longQC.py
RUN cp -r * $BIN/
RUN cd minimap2-coverage
RUN make
RUN rm -rf $BIN/minimap2-coverage
RUN cp minimap2-coverage $BIN/
RUN cd
RUN rm -rf LongQC-1.2.0b
RUN cd $BIN
RUN ln -s longQC.py longqc
RUN chmod +x *

# install dependency
RUN conda install -y \
numpy=1.19.2 \
pandas=1.2.4 \
scipy=1.6.2 \
jinja2=2.11.3 \
h5py=2.10.0 \
matplotlib=3.3.4 \
scikit-learn=0.24.1

RUN pip install \
pysam==0.16.0.1 \
edlib==1.3.8.post2

# change user to "user" defined above
USER ${USER}

# define a working dir
WORKDIR $HOME
