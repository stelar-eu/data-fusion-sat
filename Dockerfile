# For more information, please refer to https://aka.ms/vscode-docker-python
FROM ubuntu:22.04

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# install gdal
RUN apt-get update
RUN apt-get install -y pip \
                       gdal-bin \
                       libgdal-dev \    
                       curl 

RUN apt-get install -y jq

RUN rm -rf /var/lib/apt/lists/*
RUN pip install GDAL=="$(gdal-config --version).*"

# for debugging
RUN pip install debugpy

WORKDIR /app

# # install  Stelar SpatioTemporal
# RUN git clone https://github.com/stelar-eu/STELAR_spatiotemporal.git
# # Manually update the version in setup.py and install the package
# RUN  cd /app/STELAR_spatiotemporal && sed -i 's/{{VERSION_PLACEHOLDER}}/0.0.18/g' setup.py && pip install .

# Install pip requirements
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# ENV INPUT_PATH test_vista/input
# ENV OUTPUT_PATH test_vista/output
# ENV REFERENCE_PATH referenz/S2_30TYQMTI_200106_IC_DEMO.tif
# ENV RESAMPLING_METHOD bilinear
# ENV MINIO_ACCESS_KEY NT7UkSCviiEkKBbwjCQi
# ENV MINIO_SECRET_KEY G2jJ8Ut0VycvOktMERClbxRd3zECVZy8HXFcdnK2
# ENV MINIO_ENDPOINT stelar-klms.eu:9000
# ENV MINIO_BUCKET klms

# Copy the data fusion script
# only debug
COPY main.py run.sh input.json /app/  

#COPY main.py run.sh  /app/   
COPY utils /app/utils

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debu
#CMD ["python", "main.py"]
CMD ["python", "main.py", "input.json"]
#CMD ["bash", "run.sh", "token", "url", "id"]
#RUN chmod +x run.sh
#ENTRYPOINT ["./run.sh"]
