import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import hashlib
import os
from datetime import datetime

# Configuración con manejo de errores
try:
    st.set_page_config(
        page_title="Sistema de Gestión de Películas",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded"
    )
except:
    pass

# Constantes
DB_FILE = "longlist.db"
ADMIN_DB = "admin_users.db"

# -------------------- FUNCIONES MEJORADAS --------------------
def init_databases():
    """Inicializa todas las bases de datos con manejo de errores"""
    try:
        # Base de datos de películas
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS peliculas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            genero TEXT,
            idioma_original TEXT,
            traduccion_disponible TEXT,
            fecha_salida TEXT,
            pais_origen TEXT
        )
        """)
        
        # Verificar si hay datos
        count = c.execute("SELECT COUNT(*) FROM peliculas").fetchone()[0]
        if count == 0:
            ejemplos = [
                ("Inception", "Ciencia Ficción", "Inglés", "Sí", "2010-07-16", "USA"),
                ("Parasite", "Thriller", "Coreano", "Sí", "2019-05-30", "Corea del Sur"),
                ("Amélie", "Comedia", "Francés", "No", "2001-04-25", "Francia"),
                ("Spirited Away", "Animación", "Japonés", "Sí", "2001-07-20", "Japón")
            ]
            c.executemany("INSERT INTO peliculas VALUES (NULL,?,?,?,?,?,?)", ejemplos)
            conn.commit()
        conn.close()
        
        # Base de datos de administradores
        conn = sqlite3.connect(ADMIN_DB)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nombre_completo TEXT
        )
        """)
        
        # Admin por defecto
        count = c.execute("SELECT COUNT(*) FROM admins WHERE username='admin'").fetchone()[0]
        if count == 0:
            password_hash = hashlib.sha256("admin123".encode()).hexdigest()
            c.execute("INSERT INTO admins VALUES (NULL,?,?,?)", 
                     ("admin", password_hash, "Administrador Principal"))
            conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        st.error(f"Error inicializando bases de datos: {str(e)}")
        return False

def safe_db_operation(func):
    """Decorator para operaciones seguras de base de datos"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"Error de base de datos: {str(e)}")
            return None
    return wrapper

@safe_db_operation
def obtener_peliculas():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM peliculas", conn)
    conn.close()
    return df

@safe_db_operation
def agregar_pelicula(nombre, genero, idioma, traduccion, fecha, pais):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO peliculas VALUES (NULL,?,?,?,?,?,?)", 
             (nombre, genero, idioma, traduccion, fecha, pais))
    conn.commit()
    conn.close()
    return True, f"Película '{nombre}' agregada"

@safe_db_operation
def eliminar_pelicula(pelicula_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM peliculas WHERE id=?", (pelicula_id,))
    conn.commit()
    conn.close()
    return True, "Película eliminada"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@safe_db_operation
def verificar_login(username, password):
    conn = sqlite3.connect(ADMIN_DB)
    c = conn.cursor()
    password_hash = hash_password(password)
    result = c.execute("SELECT nombre_completo FROM admins WHERE username=? AND password=?", 
                      (username, password_hash)).fetchone()
    conn.close()
    return result[0] if result else None

# -------------------- INTERFAZ SIMPLIFICADA --------------------
def pagina_login():
    st.title("🎬 Sistema de Películas")
    st.subheader("Inicio de Sesión")
    
    with st.form("login"):
        user = st.text_input("Usuario")
        pwd = st.text_input("Contraseña", type="password")
        
        if st.form_submit_button("Entrar"):
            if user and pwd:
                nombre = verificar_login(user, pwd)
                if nombre:
                    st.session_state.update({
                        'logged_in': True,
                        'user': user,
                        'nombre': nombre
                    })
                    st.success(f"Bienvenido {nombre}!")
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
            else:
                st.warning("Completa ambos campos")
    
    st.info("**Demo:** usuario: admin | contraseña: admin123")

def pagina_principal():
    st.title("🎬 Gestión de Películas")
    st.write(f"👤 Usuario: {st.session_state.nombre}")
    
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()
    
    st.markdown("---")
    
    # Navegación simple
    opcion = st.radio("Navegación", ["📊 Dashboard", "🎭 Películas", "➕ Agregar"], horizontal=True)
    
    if opcion == "📊 Dashboard":
        mostrar_dashboard()
    elif opcion == "🎭 Películas":
        mostrar_peliculas()
    elif opcion == "➕ Agregar":
        agregar_pelicula_form()

def mostrar_dashboard():
    st.header("📊 Dashboard")
    
    df = obtener_peliculas()
    if df is None or df.empty:
        st.info("No hay películas registradas")
        return
    
    # Métricas
    cols = st.columns(4)
    with cols[0]: st.metric("Total", len(df))
    with cols[1]: st.metric("Géneros", df['genero'].nunique())
    with cols[2]: st.metric("Idiomas", df['idioma_original'].nunique())
    with cols[3]: st.metric("Países", df['pais_origen'].nunique())
    
    # Gráficos simples
    col1, col2 = st.columns(2)
    
    with col1:
        if 'genero' in df.columns:
            fig = px.pie(df, names='genero', title='Géneros')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'traduccion_disponible' in df.columns:
            fig = px.pie(df, names='traduccion_disponible', title='Traducciones')
            st.plotly_chart(fig, use_container_width=True)
    
    # Lista de películas
    st.subheader("🎬 Lista de Películas")
    st.dataframe(df[['nombre', 'genero', 'idioma_original', 'pais_origen']])

def mostrar_peliculas():
    st.header("🎭 Gestión de Películas")
    
    df = obtener_peliculas()
    if df is None or df.empty:
        st.info("No hay películas")
        return
    
    # Búsqueda simple
    busqueda = st.text_input("🔍 Buscar por nombre")
    if busqueda:
        df = df[df['nombre'].str.contains(busqueda, case=False, na=False)]
    
    st.dataframe(df, use_container_width=True)
    
    # Eliminar película
    if not df.empty:
        pelicula_eliminar = st.selectbox("Seleccionar para eliminar", df['nombre'].values)
        if st.button("🗑️ Eliminar", type="primary"):
            pelicula_id = df[df['nombre'] == pelicula_eliminar].iloc[0]['id']
            success, msg = eliminar_pelicula(pelicula_id)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

def agregar_pelicula_form():
    st.header("➕ Agregar Película")
    
    with st.form("agregar"):
        nombre = st.text_input("Nombre*")
        genero = st.text_input("Género*")
        idioma = st.text_input("Idioma*")
        traduccion = st.selectbox("Traducción*", ["Sí", "No"])
        fecha = st.date_input("Fecha*")
        pais = st.text_input("País*")
        
        if st.form_submit_button("✅ Agregar"):
            if all([nombre, genero, idioma, pais]):
                success, msg = agregar_pelicula(
                    nombre, genero, idioma, traduccion,
                    fecha.strftime("%Y-%m-%d"), pais
                )
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.warning("Completa los campos obligatorios (*)")

def main():
    # Inicializar estado
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # Inicializar bases de datos
    if not init_databases():
        st.error("Error crítico: No se pudieron inicializar las bases de datos")
        return
    
    # Mostrar interfaz
    if not st.session_state.logged_in:
        pagina_login()
    else:
        pagina_principal()

if __name__ == "__main__":
    main()
