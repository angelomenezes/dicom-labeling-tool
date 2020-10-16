# DICOM Viewer with Labeling Tool

This repository contains a simple web-based DICOM viewer built using Streamlit. It also has a tool to generate a .JSON to annotate which slices of a specific series have anomalies. This was meant to be a weekend project to learn how to work with Streamlit, Docker and Heroku but it took a little more than that to figure out how to set up everything and to make it look good.

[Medium post]() -> (to be released soon)

[Demo hosted on Heroku]([dicom-annotator.](https://dicom-annotator.herokuapp.com/))

![](sample/webapp-sample.gif)

The tool only deals with zip files that have one or more folders, normally represented as series, with dicom files inside. A [sample](sample/sample.zip) of an acceptable zip file can be checked inside the sample folder.
Zip files can be uploaded via public shared URLs from `Google Drive` or using the file upload widget. 

As the demo is hosted on Heroku and their free tier dyno has limited memory resources, the uploaded zip files are limited to 100MB. However, this restriction can be adjusted by code when running the web viewer locally.


## Setup
### Docker
```bash
git clone https://github.com/angelomenezes/dicom-labeling-tool.git
cd dicom-labeling-tool/

docker build ./ --tag webapp:v1
docker run -it --rm=true webapp:v1 /bin/bash
docker container run -p 8501:8501 webapp:v1
``` 
Open the browser at http://localhost:8501/.

When you finish working with the container, run the following command to terminate the process:
```bash
docker rm --force webapp
```


### Conda
Make sure you have [Anaconda](https://www.anaconda.com/) installed since it is the easiest way to setup GDCM on Python3 which is a requirement for the pydicom library.

```bash
conda install -c conda-forge -y gdcm

git clone https://github.com/angelomenezes/dicom-labeling-tool.git

cd dicom-labeling-tool/webapp/
pip install -r /requirements.txt

streamlit run DICOM.py
```

## License
[`MIT`](LICENSE)

## Contact
Any comments, suggestions or contributions are welcome. You can contact me at angelomenezes.eng@gmail.com.