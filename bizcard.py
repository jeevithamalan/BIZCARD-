import streamlit as st
import psycopg2
from streamlit_option_menu import option_menu
import easyocr
from PIL import Image
import pandas as pd
import numpy as np
import re   ##regular expression
import io
import time

##text data

def image_to_text(path):
    input_pic=Image.open(path)
    img_array=np.array(input_pic)

    reader=easyocr.Reader(['en'])
    text=reader.readtext(img_array,detail=0)
    return text

def extract_text(texts):
    extract_dic = {
        "Name": [],"Designation": [],"Company_Name": [],"Contact": [],"EMail": [],"Website": [],"Address": [],"Pincode": []}

    extract_dic["Name"].append(texts[0])
    lower = texts[1].lower()
    extract_dic["Designation"].append(lower)

    for i in range(2, len(texts)):
        if texts[i].startswith("+") or '-' in texts[i] or (texts[i].replace("-", " ").isdigit() and '-' in texts[i]):
            extract_dic["Contact"].append(texts[i])
            
        elif '@' in texts[i] and '.com' in texts[i]:
            extract_dic["EMail"].append(texts[i])
            
        elif 'www' in texts[i] or 'WWW' in texts[i] or 'wwW' in texts[i] or 'Www' in texts[i]:
            lower = texts[i].lower()
            extract_dic["Website"].append(lower)
            
        elif 'TamilNadu' in texts[i] or 'Tamil Nadu' in texts[i] or texts[i].isdigit():
            extract_dic["Pincode"].append(texts[i])
            
        elif re.match(r'^[A-Z a-z]', texts[i]):
            extract_dic["Company_Name"].append(texts[i])
            
        else:
            removeextra=re.sub(r'[,;]','',texts[i])
            extract_dic["Address"].append(removeextra)
            
    for key , value  in extract_dic.items():
        if len(value)>0:
            concad="".join(value)
            extract_dic[key]=[concad]
        else:
            value ="NA"
            extract_dic[key]=[value]         
            
    return extract_dic

st.set_page_config(layout="wide")
with st.sidebar:   
    
    
    selected = option_menu("Main Menu", ['Upload Image','View & Modify','Delete'],)
        

if selected=="Upload Image":                  
    uploaded_files = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])

    if uploaded_files is not None:
        st.image(uploaded_files,width=330)  
        
        text_img = image_to_text(uploaded_files)
        text_dict = extract_text(text_img)
        
        if text_dict:
            st.success("Text is Extracted Successfully")
            df = pd.DataFrame(text_dict)
            st.dataframe(df)
            
        button1=st.button(":red[Save Text]",use_container_width=True)
        
        if button1:            
            mydb = psycopg2.connect(host="localhost",
                user="postgres", password="root",
                database="bizcard",port="5432")
            cursor = mydb.cursor()

            create_table = '''create table if not exists bizcard_details(
                                name varchar(99),designation varchar(99),
                                company_name varchar(99),contact varchar(99),
                                email varchar(99),website text,
                                address text,pincode varchar(99))'''

            cursor.execute(create_table)
            mydb.commit()            
            cursor = mydb.cursor()
            insert_data = '''insert into bizcard_details(name,designation,company_name,contact,
                                email,website,address,pincode) values(%s,%s,%s,%s,%s,%s,%s,%s)'''
            data =df.values.tolist()
            cursor.executemany(insert_data, data)
            mydb.commit()
            st.success("Above the Text data Inserted Successfully")
elif selected=="View & Modify":                 
    selected_option = st.selectbox("View or Modify options", ["Select Below Options", "Preview text", "Modify text"])
    if selected_option == "Select Below Options":
        pass
    elif selected_option == "Preview text":
                    mydb = psycopg2.connect(host="localhost",user="postgres", password="root",
                                            database="bizcard",port="5432")
                    cursor = mydb.cursor()                
                    select_data="select * from bizcard_details"
                    cursor.execute(select_data)
                    table=cursor.fetchall()
                    mydb.commit()
                    table_df=pd.DataFrame(table,columns=("name","designation","company_name","contact","email","website","address","pincode"))
                    table_df        
    elif selected_option == "Modify text":
                mydb = psycopg2.connect(host="localhost",user="postgres", password="root",
                                        database="bizcard",port="5432")
                cursor = mydb.cursor()                
                select_data="select * from bizcard_details"
                cursor.execute(select_data)
                table=cursor.fetchall()
                mydb.commit()
                table_df=pd.DataFrame(table,columns=("name","designation","company_name","contact","email","website","address","pincode"))

                select_name=st.selectbox("Select the Name",table_df["name"])
                df3=table_df[table_df["name"]==select_name]
                
                df4=df3.copy()
                st.dataframe(df4)   
                
                coll1,coll2=st.columns(2)
                with coll1:     
                    modi_name=st.text_input("Name",df3["name"].unique()[0])      
                    modi_design=st.text_input("Designation",df3["designation"].unique()[0])    
                    modi_company=st.text_input("Company_name",df3["company_name"].unique()[0])    
                    modi_contact=st.text_input("Contact",df3["contact"].unique()[0])  
                    
                    df4["name"]=modi_name
                    df4["designation"]=modi_design
                    df4["company_name"]=modi_company
                    df4["contact"]=modi_contact
                                        
    
                with coll2:     
                    modi_mail=st.text_input("Email",df3["email"].unique()[0])      
                    modi_web=st.text_input("Website",df3["website"].unique()[0])    
                    modi_address=st.text_input("Address",df3["address"].unique()[0])    
                    modi_pincode=st.text_input("Pincode",df3["pincode"].unique()[0]) 
                    
                    df4["email"]=modi_mail
                    df4["website"]=modi_web
                    df4["address"]=modi_address
                    df4["pincode"]=modi_pincode
                
                st.dataframe(df4)    
                
                coll1, coll2 = st.columns(2)
                with coll1:
                    button2 = st.button("Modify Text", use_container_width=True)
                    mydb = psycopg2.connect(host="localhost", user="postgres", password="root", database="bizcard", port="5432")
                    cursor = mydb.cursor()

                if button2:
                                               
                    cursor.execute(f"delete from bizcard_details where name='{select_data}'")
                    mydb.commit()

                    insert_data = '''insert into bizcard_details(name,designation,company_name,contact,email,website,address,pincode)
                                    values(%s,%s,%s,%s,%s,%s,%s,%s)'''
                    data = df4.values.tolist()
                    cursor.executemany(insert_data, data)
                    mydb.commit()
                    st.success("Above the Text data Modify Successfully")
                    
elif selected == "Delete": 
    mydb = psycopg2.connect(host="localhost", user="postgres", password="root", database="bizcard", port="5432")
    cursor = mydb.cursor()

    coll1, coll2 = st.columns(2)
    with coll1:
        select_data = "SELECT name FROM bizcard_details"
        cursor.execute(select_data)
        table5 = cursor.fetchall()
        mydb.commit()

        names = [i[0] for i in table5]
        name_select = st.selectbox("Select the Name", names)

        if st.button("Delete", use_container_width=True):
            delete_query = "DELETE FROM bizcard_details WHERE name = %s"
            cursor.execute(delete_query, (name_select,))
            mydb.commit()
            st.success("Deleted Successfully")