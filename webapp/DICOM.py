import streamlit as st
from src.utils import *
import gc

# Hide FileUploader deprecation
st.set_option('deprecation.showfileUploaderEncoding', False)

# Hide streamlit header
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""

st.markdown(hide_streamlit_style, unsafe_allow_html=True) 

data_key = 'has_data'
width = 400
data_is_ready = False
data_has_changed = False

if not os.path.isdir('./data/'):
    os.makedirs('./data/')

if not os.path.isdir('./temp'):
    os.makedirs('./temp/')

# Adjusting images to be centralized.
with open("style.css") as f:
    st.markdown('<style>{}</style>'.format(f.read()), unsafe_allow_html=True)
    
if __name__ == "__main__": 
    
    state = get_state()

    st.title('DICOM Viewer')

    st.sidebar.title('DICOM Labeling Tool')

    demo_button = st.sidebar.checkbox('Demo', value=False)
    
    url_input = st.sidebar.text_input('Enter the Google Drive shared url for the .dcm files')
    
    st.sidebar.markdown('<h5>MAX FILE SIZE: 100 MB</h5>', unsafe_allow_html=True)
    st.sidebar.markdown(' ')
    st.sidebar.markdown('or')

    file_uploaded =  st.sidebar.file_uploader("Upload a .zip with .dcm files (slower than GDrive)", type="zip")

    if demo_button:
        url_input = 'https://drive.google.com/file/d/1ESRZpJA92g8L4PqT2adCN3hseFbnw9Hg/view?usp=sharing'

    if file_uploaded:
        if not state[data_key]:
            if does_zip_have_dcm(file_uploaded):
                store_data(file_uploaded)
                data_has_changed = True
    
    if url_input:
        if not state[data_key]:
            if download_zip_from_url(url_input):
                data_has_changed = True

    if st.sidebar.button('---------- Refresh input data ----------'):
        clear_data_storage(temp_data_directory + get_report_ctx().session_id + '/')
        clear_data_storage(temp_zip_folder)
        st.caching.clear_cache()
        url_input = st.empty()
        data_is_ready = False
        data_has_changed = False
        state[data_key] = False
        state.clear()

    if data_has_changed:
        valid_folders = get_DCM_valid_folders(temp_data_directory + get_report_ctx().session_id + '/')
        
        for folder in valid_folders:
            state[folder.split('/')[-1]] = ('', '', {'Anomaly': 'Bleeding', 'Slices': ''})

        state[data_key] = True
        state['valid_folders'] = valid_folders
        state.last_serie = ''

        data_has_changed = False
    
    if state[data_key]:
        data_is_ready = True
    
    if data_is_ready:
        series_names = get_series_names(state['valid_folders'])
        
        selected_serie = st.selectbox('Select a series', series_names, index=0)
        
        st.markdown('<h2>Patient Info</h2>', unsafe_allow_html=True)
        display_info = st.checkbox('Display data', value=True)
        
        if state.last_serie != selected_serie:
            st.caching.clear_cache()
            state.last_serie = selected_serie

        img3d, info = processing_data(state['valid_folders'][series_names.index(selected_serie)] + '/')
            
        if display_info:
            st.dataframe(info)
        
        options = st.multiselect('Choose the views of the DICOM.', 
                                ['Axial', 'Coronal', 'Sagittal'], 
                                ['Axial'])
        
        if 'Axial' in options:
            axial_slider = st.slider(
                'Axial Slices',
                0, img3d.shape[2] - 1, (img3d.shape[2] - 1)//2
            )
            axial_max = int(img3d[:, :, axial_slider].max())
            axial_threshold = st.slider(
                'Axial Color Threshold',
                0, 100, 50
            )
            axial_threshold = axial_max * ((2 * axial_threshold / 100) - 1)
            st.image(normalize_image(filter_image(axial_threshold, img3d[:, :, axial_slider])),
                                            caption='Slice {}'.format(axial_slider), width=width)

        if 'Coronal' in options:
            coronal_slider = st.slider(
                'Coronal Slices',
                0, img3d.shape[0] - 1, (img3d.shape[0] - 1)//2
            )
            coronal_max = int(img3d[coronal_slider, :, :].max())
            coronal_threshold = st.slider(
                'Coronal Color Threshold',
                0, 100, 50
            )
            coronal_threshold = coronal_max * ((2 * coronal_threshold / 100) - 1)
            st.image(normalize_image(filter_image(coronal_threshold, resize(ndimage.rotate(img3d[coronal_slider, :, :].T, 180), (img3d.shape[0],img3d.shape[0])))), caption='Slice {}'.format(coronal_slider), width=width)

        if 'Sagittal' in options:
            sagittal_slider = st.slider(
                'Sagittal Slices',
                0, img3d.shape[1] - 1, (img3d.shape[1] - 1)//2
            )
            sagittal_max = int(img3d[:, sagittal_slider, :].max())
            sagittal_threshold = st.slider(
                'Sagittal Color Threshold',
                0, 100, 50
            )
            sagittal_threshold = sagittal_max * ((2 * sagittal_threshold / 100) - 1)
            st.image(normalize_image(filter_image(sagittal_threshold, resize(ndimage.rotate(img3d[:, sagittal_slider, :], 90), (img3d.shape[0],img3d.shape[0])))), caption='Slice {}'.format(sagittal_slider), width=width)

        if options:
            state[selected_serie][2]['Anomaly'] = st.sidebar.text_input('Anomaly Label', value=state[selected_serie][2]['Anomaly'])
            
        st.sidebar.markdown('<h1 style=\'font-size:0.65em\'> Example of annotation with slices: 0-11; 57-59; 112; </h1> ', unsafe_allow_html=True)

        if 'Axial' in options:
            state[selected_serie][2]['Slices'] = st.sidebar.text_input("Axial Annotation - Slices with Anomaly", value=state[selected_serie][2]['Slices'])

        if options:
            annotation_selected = st.sidebar.multiselect('Annotated series to be included in the .json', series_names, series_names)
            json_selected = {serie: state[serie][2] for serie in annotation_selected}
            
            if st.checkbox('Check Annotations.json', value=True):
                st.write(json_selected)
            
            download_button_str = download_button(json_selected, 'Annotation.json', 'Download Annotation.json')
            st.sidebar.markdown(download_button_str, unsafe_allow_html=True) 

        del img3d, info

    if st.sidebar.checkbox('Notes', value=True):
        st.sidebar.markdown('1. It does not recognize zip folders inside other zip folders.')
        st.sidebar.markdown('2. It only recognizes series with two or more .dcm files.')
        st.sidebar.markdown('3. You can use the arrow keys to change the slider widgets.')
        st.sidebar.markdown('3. Uploaded files are cached until the heroku session becomes idle (30 min).'
                            ' Then, they are automatically deleted.')
        st.sidebar.markdown('4. If you want to manually reset/delete previously uploaded data via URL, ' 
                            'clear the text input, and press the button to refresh input data. '
                            'In case you are using the File Uploader widget, perform the same '
                            'actions described above and then refresh the page with F5. ')
    
    gc.collect()
    state.sync()