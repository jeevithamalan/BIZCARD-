import streamlit as st
import pandas as pd
import psycopg2
import easyocr
import cv2
import os
import matplotlib.pyplot as plt
import re
import numpy as np

# Streamlit page setting
st.set_page_config(layout='wide')

st.title(" :blue[BizCard: Extracting Business Card Data with OCR]")

col1, col2 = st.columns([1, 4])
with col1:
    option = st.radio("", ["Home Page", "Upload the card and Extract text", "Modify Details"])
    if option == "Modify Details":
        option1 = st.radio("", ["Modify", "Delete"])

    # Initializing EasyOCR reader
    reader = easyocr.Reader(['en'], gpu=False)

# Function to establish connection to PostgreSQL
def create_connection():
    return psycopg2.connect(
        host='localhost',
        user='postgres',
        password='root',
        database='bizcardx',
        port=5432
    )

# Creating table if it doesn't exist
try:
    with create_connection() as mydb:
        mycursor = mydb.cursor()
        mycursor.execute('''CREATE TABLE IF NOT EXISTS biz_cardz
                            (id SERIAL PRIMARY KEY,
                            name TEXT,
                            company_name TEXT,
                            designation TEXT,
                            mobile_number VARCHAR(50),
                            email TEXT,
                            website TEXT,
                            street TEXT,
                            city TEXT,
                            state TEXT,
                            pin_code VARCHAR(10),
                            image BYTEA)''')
        mydb.commit()
        print("Table 'biz_cardz' created successfully.")
except psycopg2.OperationalError as e:
    print(f"Error: {e}")

if option == 'Upload the card and Extract text':
    with col2:
        st.markdown(" :green[Upload Your Business Card]")
        selected_card = st.file_uploader("Upload business card here", label_visibility="collapsed", type=["png", "jpeg", "jpg"])

    if selected_card is not None:
        # Ensure the upload directory exists
        upload_dir = os.path.join(os.getcwd(), "uploaded_card")
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        # Save the uploaded file to the upload directory
        saved_img_path = os.path.join(upload_dir, selected_card.name)
        with open(saved_img_path, "wb") as f:
            f.write(selected_card.getbuffer())

        # easy OCR
        reader = easyocr.Reader(['en'], gpu=False)
        text_result = reader.readtext(saved_img_path, detail=0, paragraph=False)

        # Converting image to binary to upload to SQL database
        def binary(file):
            with open(file, 'rb') as file:
                binaryData = file.read()
            return binaryData

        details = {
            "name": [],
            "company_name": [],
            "designation": [],
            "mobile_number": [],
            "email": [],
            "website": [],
            "street": [],
            "city": [],
            "state": [],
            "pin_code": [],
            "image": binary(saved_img_path)
        }

        def extract_text(text):
            for idx, item in enumerate(text):
                if idx == 0:
                    details["name"].append(item)
                elif idx == len(text) - 1:
                    details["company_name"].append(item)
                elif idx == 1:
                    details["designation"].append(item)
                elif "-" in item:
                    details["mobile_number"].append(item)
                    if len(details["mobile_number"]) == 2:
                        details["mobile_number"] = " & ".join(details["mobile_number"])
                elif "@" in item:
                    details["email"].append(item)
                elif "www" in item.lower() or "WWW" in item:
                    details["website"].append(item)
                if re.findall('^[0-9].+, [a-zA-Z]+', item):
                    details["street"].append(item.split(',')[0])
                elif re.findall('[0-9] [a-zA-Z]+', item):
                    details["street"].append(item)
                match1 = re.findall('.+St , ([a-zA-Z]+).+', item)
                match2 = re.findall('.+St,, ([a-zA-Z]+).+', item)
                match3 = re.findall('^[E].*', item)
                if match1:
                    details["city"].append(match1[0])
                elif match2:
                    details["city"].append(match2[0])
                elif match3:
                    details["city"].append(match3[0])
                state_match = re.findall('[a-zA-Z]{9} +[0-9]', item)
                if state_match:
                    details["state"].append(item[:9])
                elif re.findall('^[0-9].+, ([a-zA-Z]+);', item):
                    details["state"].append(item.split()[-1])
                if len(details["state"]) == 2:
                    details["state"].pop(0)
                if len(item) >= 6 and item.isdigit():
                    details["pin_code"].append(item)
                elif re.findall('[a-zA-Z]{9} +[0-9]', item):
                    details["pin_code"].append(item[10:])

        extract_text(text_result)

        def image_preview(image, res):
            for (box, text, prob) in res:
                (top_left, top_right, bottom_right, bottom_left) = box
                top_left = (int(top_left[0]), int(top_left[1]))
                top_right = (int(top_right[0]), int(top_right[1]))
                bottom_right = (int(bottom_right[0]), int(bottom_right[1]))
                bottom_left = (int(bottom_left[0]), int(bottom_left[1]))
                cv2.rectangle(image, top_left, bottom_right, (0, 0, 255), 2)
            plt.rcParams['figure.figsize'] = (15, 15)
            plt.axis('off')
            plt.imshow(image)

        col3, col4 = st.columns(2, gap="large")
        with col3:
            st.markdown("#     ")
            with st.spinner("Please wait processing image..."):
                st.set_option('deprecation.showPyplotGlobalUse', False)
                image = cv2.imread(saved_img_path)
                res = reader.readtext(saved_img_path)
                st.header(" :blue[Image Processed and Data Extracted]")
                st.pyplot(image_preview(image, res))

            with col4:
                st.markdown("#     ")
                st.markdown("#     ")
                for box, text, prob in res:
                    st.write(f"Text  : {text}")

        df = pd.DataFrame(details)
        st.write(df)

        if st.button("Upload to Database"):
            with create_connection() as mydb:
                mycursor = mydb.cursor()
                for i, row in df.iterrows():
                    sql_check = "SELECT COUNT(*) FROM biz_cardz WHERE name = %s"
                    mycursor.execute(sql_check, (row['name'],))
                    result = mycursor.fetchone()

                    if result[0] > 0:
                        st.warning(f"{row['name']} card already exists in the database")
                    else:
                        sql_insert = """INSERT INTO biz_cardz(company_name, name, designation, mobile_number, email, website, street, city, state, pin_code, image)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                        # Use tuple(row) instead of tuple(row.values())
                        mycursor.execute(sql_insert, tuple(row))
                        mydb.commit()
                        st.success("Uploaded to database successfully!")



if option == "Modify Details":
    with col2:
        with create_connection() as mydb:
            mycursor = mydb.cursor()
            mycursor.execute("SELECT * FROM biz_cardz")
            df = pd.DataFrame(mycursor.fetchall(), columns=[desc[0] for desc in mycursor.description])

        st.write(' :green[Database Table]')
        st.dataframe(df)
        st.button('Show Changes')

        if option1 == "Modify":
            col3, col4 = st.columns(2)
            with col3:
                st.write(' :green[Select which card you want to change]')
                names = ['Please select one', 'id', 'name', 'email']
                selected = st.selectbox('', names)
                if selected != 'Please select one':
                    select = ['Please select one'] + list(df[selected])
                    select_detail = st.selectbox(f'**Select the {selected}**', select)
                    with col4:
                        if select_detail != 'Please select one':
                            df1 = df[df[selected] == select_detail].reset_index()
                            select_modify = st.selectbox('', ['Please select one'] + list(df.columns))
                            if select_modify != 'Please select one':
                                a = df1[select_modify][0]
                                st.write(f'Do you want to change {select_modify}: **{a}** ?')
                                modified = st.text_input(f'**Enter the {select_modify} to be modified.**')
                                if modified:
                                    st.write(f'{select_modify} **{a}** will change as **{modified}**')
                                with col3:
                                    if st.button("Commit Changes"):
                                        update_query = f"UPDATE biz_cardz SET {select_modify} = %s WHERE {selected} = %s"
                                        mycursor.execute(update_query, (modified, select_detail))
                                        mydb.commit()
                                        st.success("Changes committed successfully!")

        if option1 == 'Delete':
            col1, col2, col3 = st.columns([1, 1, 5])
            with col1:
                st.write(' :green[Select where to delete the details]')
                names = ['Please select one', 'name', 'email']
                delete_selected = st.selectbox('', names)
                if delete_selected != 'Please select one':
                    select = df[delete_selected]
                    delete_select_detail = st.selectbox(f'**Select the {delete_selected} to remove**', ['Please select one'] + list(select))
                    if delete_select_detail != 'Please select one':
                        st.write(f'Do you want to delete **{delete_select_detail}** card details ?')
                        delete = st.button('Yes I do')
                        if delete:
                            delete_query = f"DELETE FROM biz_cardz WHERE {delete_selected} = %s"
                            mycursor.execute(delete_query, (delete_select_detail,))
                            mydb.commit()
                            st.success("Data Deleted successfully", icon='✅')

