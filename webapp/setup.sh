mkdir -p /root/.streamlit

echo -e "\
[general]\n\
email = \"\"\n\
" > /root/.streamlit/credentials.toml

echo -e "\
[server]\n\
enableCORS = false\n\
" > /root/.streamlit/config.toml