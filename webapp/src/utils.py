import os
import pydicom
import numpy as np
import sys
from scipy import ndimage
from skimage.transform import resize
import glob
import pandas as pd
import base64
import json
import pickle
import re
import uuid
import shutil
import zipfile
import time
import functools
import random
import string
from google_drive_downloader import GoogleDriveDownloader as gdd

import streamlit as st
from streamlit.hashing import _CodeHasher
from streamlit.report_thread import get_report_ctx
from streamlit.server.server import Server

MAX_SIZE = 110000000 # 110MB
temp_data_directory = './data/'
temp_zip_folder = './temp/'
temp_zip_file = temp_zip_folder + 'data.zip'

def store_data(file, temporary_location=temp_zip_file):
    
    st.warning('Loading data from zip.')

    with open(temporary_location, 'wb') as out:
        out.write(file.getbuffer())
    
    if is_zip_oversized(temporary_location):
        st.warning('Oversized zip file.')
        clear_data_storage(temporary_location)
        return False

    with zipfile.ZipFile(temporary_location) as zip_ref:            
        zip_ref.extractall(temp_data_directory + get_report_ctx().session_id + '/')
        
    clear_data_storage(temp_zip_folder)

    return True


def is_valid_url(url):
    regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None

def is_zip_oversized(path, max_size=MAX_SIZE):
    if os.path.getsize(path) > max_size:
        return True
    return False

def download_zip_from_url(url, dest_path=temp_zip_file): 
    
    if is_valid_url(url):

        url_string = url.split('/')
        file_id = max(url_string, key=len)
        st.warning('Loading data from the web.')
        gdd.download_file_from_google_drive(file_id=file_id,
                                            dest_path=dest_path,
                                            overwrite=True)
        
        if does_zip_have_dcm(dest_path):
            
            if is_zip_oversized(dest_path):
                st.warning('Oversized zip file.')
                clear_data_storage(dest_path)
                return False

            with zipfile.ZipFile(dest_path) as zip_ref:            
                zip_ref.extractall(temp_data_directory + get_report_ctx().session_id + '/')
        
            clear_data_storage(temp_zip_folder)

            return True
    else:
        st.warning('Not valid URL.')

    return False
        
@st.cache(show_spinner=False)
def processing_data(path):
    return read_DICOM_slices(path)

def clear_data_storage(path):

    if os.path.isfile(path):
        os.remove(path)

    if os.path.isdir(path):
        shutil.rmtree(path)

def get_series_names(folder_names):
    return [name.split('/')[-1] for name in folder_names]

def number_of_dcm_files(folder):
    counter = 0
    files = os.listdir(folder)
    for file in files:
        if file[-4:] == '.dcm':
            counter += 1
    del files
    return counter

def is_zip_valid(path):
    try:
        check_zip = zipfile.ZipFile(path)
        check_zip.close()
    except:
        st.warning('Not a valid zip file.')
        clear_data_storage(temp_zip_folder)
        return False
    return True

def does_zip_have_dcm(file):
    if is_zip_valid(file):
        with zipfile.ZipFile(file) as zip_ref:
            name_list = zip_ref.namelist()
            for item in name_list:
                if item[-4:] == '.dcm':
                    return True
        st.warning('Zip folder does not have folders with DICOM files.')
    return False

def get_DCM_valid_folders(folder, min_dcm=2):
    DCM_valid_folder = []
    for root, directories, files in os.walk(folder):
        if directories: # More than one directory
            for name in directories:
                n_of_dcm = number_of_dcm_files(os.path.join(root, name))
                if n_of_dcm >= min_dcm:
                    DCM_valid_folder.append(os.path.join(root, name))
    return DCM_valid_folder

def download_button(object_to_download, download_filename, button_text, pickle_it=False):
    
    if pickle_it:
        try:
            object_to_download = pickle.dumps(object_to_download)
        except pickle.PicklingError as e:
            st.write(e)
            return None

    else:
        if isinstance(object_to_download, bytes):
            pass

        elif isinstance(object_to_download, pd.DataFrame):
            object_to_download = object_to_download.to_csv(index=False)

        # Try JSON encode for everything else
        else:
            object_to_download = json.dumps(object_to_download)

    try:
        # some strings <-> bytes conversions necessary here
        b64 = base64.b64encode(object_to_download.encode()).decode()

    except AttributeError as e:
        b64 = base64.b64encode(object_to_download).decode()

    button_uuid = str(uuid.uuid4()).replace('-', '')
    button_id = re.sub('\d+', '', button_uuid)

    custom_css = f""" 
        <style>
            #{button_id} {{
                background-color: rgb(255, 255, 255);
                color: rgb(38, 39, 48);
                padding: 0.25em 0.38em;
                position: relative;
                text-decoration: none;
                border-radius: 4px;
                border-width: 1px;
                border-style: solid;
                border-color: rgb(230, 234, 241);
                border-image: initial;
                display: flex;
                justify-content: center;
            }} 
            #{button_id}:hover {{
                border-color: rgb(246, 51, 102);
                color: rgb(246, 51, 102);
            }}
            #{button_id}:active {{
                box-shadow: none;
                background-color: rgb(246, 51, 102);
                color: white;
                }}
        </style> """

    dl_link = custom_css + f'<a download="{download_filename}" id="{button_id}" href="data:file/txt;base64,{b64}">{button_text}</a><br></br>'

    return dl_link

def filter_image(threshold_value, img):
    img_ = img.copy()
    img_max = img.max()
    img_min = img.min()
    img_ += threshold_value
    img_[img_ < img_min] = img_min
    img_[img_ > img_max] = img_max
    return img_

def normalize_image(img, axis=None):
    return (img - img.min()) / (img.max() - img.min())


def display_info(path):
    columns = ['PatientID', 'PatientName', 'StudyDescription', 'PatientBirthDate', 'StudyDate', 'Modality', 'Manufacturer', 'InstitutionName', 'ProtocolName']
    col_dict = {col: [] for col in columns}
    dicom_object = pydicom.dcmread(path + os.listdir(path)[0])
    
    for col in columns: 
        col_dict[col].append(str(getattr(dicom_object, col)))
    
    df = pd.DataFrame(col_dict).T
    df.columns = ['Patient']
    return df

def read_DICOM_slices(path):
    
    # Load the DICOM files
    files = []

    for fname in glob.glob(path + '*', recursive=False):
        if fname[-4:] == '.dcm': # Read only dicom files inside folders.
            files.append(pydicom.dcmread(fname))

    # Skip files with no SliceLocation
    slices = []
    skipcount = 0
    for f in files:
        if hasattr(f, 'SliceLocation'):
            slices.append(f)
        else:
            skipcount = skipcount + 1

    slices = sorted(slices, key=lambda s: s.SliceLocation)

    img_shape = list(slices[0].pixel_array.shape)
    img_shape.append(len(slices))
    img3d = np.zeros(img_shape)

    # Fill 3D array with the images from the files
    for i, img2d in enumerate(slices):
        img3d[:, :, i] = img2d.pixel_array

    columns = ['PatientID', 'PatientName', 'StudyDescription', 'PatientBirthDate', 'StudyDate', 'Modality', 'Manufacturer', 'InstitutionName', 'ProtocolName']
    col_dict = {col: [] for col in columns}

    try:
        for col in columns: 
            col_dict[col].append(str(getattr(files[0], col)))
        
        df = pd.DataFrame(col_dict).T
        df.columns = ['Patient']
    except:
        df = pd.DataFrame([])

    del files, slices, columns, col_dict

    return img3d, df

class SessionState:

    def __init__(self, session, hash_funcs):
        """Initialize SessionState instance."""
        self.__dict__["_state"] = {
            "data": {},
            "hash": None,
            "hasher": _CodeHasher(hash_funcs),
            "is_rerun": False,
            "session": session
        }

    def __call__(self, **kwargs):
        """Initialize state data once."""
        for item, value in kwargs.items():
            if item not in self._state["data"]:
                self._state["data"][item] = value

    def __getitem__(self, item):
        """Return a saved state value, None if item is undefined."""
        return self._state["data"].get(item, None)
        
    def __getattr__(self, item):
        """Return a saved state value, None if item is undefined."""
        return self._state["data"].get(item, None)

    def __setitem__(self, item, value):
        """Set state value."""
        self._state["data"][item] = value

    def __setattr__(self, item, value):
        """Set state value."""
        self._state["data"][item] = value
    
    def clear(self):
        """Clear session state and request a rerun."""
        self._state["data"].clear()
        self._state["session"].request_rerun()
    
    def sync(self):
        """Rerun the app with all state values up to date from the beginning to fix rollbacks."""

        # Ensure to rerun only once to avoid infinite loops
        # caused by a constantly changing state value at each run.
        #
        # Example: state.value += 1
        if self._state["is_rerun"]:
            self._state["is_rerun"] = False
        
        elif self._state["hash"] is not None:
            if self._state["hash"] != self._state["hasher"].to_bytes(self._state["data"], None):
                self._state["is_rerun"] = True
                self._state["session"].request_rerun()

        self._state["hash"] = self._state["hasher"].to_bytes(self._state["data"], None)


def get_session():
    session_id = get_report_ctx().session_id
    session_info = Server.get_current()._get_session_info(session_id)

    if session_info is None:
        raise RuntimeError("Couldn't get your Streamlit Session object.")
    
    return session_info.session


def get_state(hash_funcs=None):
    session = get_session()

    if not hasattr(session, "_custom_session_state"):
        session._custom_session_state = SessionState(session, hash_funcs)

    return session._custom_session_state