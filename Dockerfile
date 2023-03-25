#FROM heroku/miniconda
FROM continuumio/miniconda3:4.8.2

# Grab requirements.txt
ADD ./webapp/requirements.txt /tmp/requirements.txt

# Install Python 3.6.10, specific for working with gdcm
RUN conda install python=3.6.10

# Install GDCM
RUN conda install -c conda-forge -y gdcm

# Install dependencies
RUN pip3 install -r /tmp/requirements.txt

# Add the code
ADD ./webapp /opt/webapp/
WORKDIR /opt/webapp

RUN bash setup.sh

ENV PORT=8085

EXPOSE 8501

CMD streamlit run DICOM.py --server.port $PORT