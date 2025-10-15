import streamlit as st
import sqlite3
import hashlib
import os
from datetime import datetime

# Configuración
st.set_page_config(
    page_title="Sistema de Películas",
    page_icon="🎬",
    layout="wide"
)

# Constantes
DB_FILE = "peliculas.db"

def init_database():
    """Inicializar base de datos simple"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Tabla de películas
        c.execute('''
            CREATE TABLE IF NOT EXISTS peliculas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                genero TEXT,
                idioma TEXT,
                traduccion TEXT,
                fecha TEXT,
                pais TEXT
            )
        ''')
        
        # Tabla de usuarios
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                nombre TEXT
            )
        ''')
        
        # Usuario por defecto
        c.execute("SELECT COUNT(*) FROM usuarios WHERE username='admin'")
        if c.fetchone()[0] == 0:
            password_hash = hashlib.sha256("admin123".encode()).hexdigest()
            c.execute("INSERT INTO usuarios (username, password, nombre) VALUES (?, ?, ?)",
                     ("admin", password_hash, "Administrador"))
        
        # Datos de ejemplo
        c.execute("SELECT COUNT(*) FROM peliculas")
        if c.fetchone()[0] == 0:
            peliculas = [
                ("Inception", "Ciencia Ficción", "Inglés", "Sí", "2010-07-16", "USA"),
                ("El Laberinto del Fauno", "Fantasía", "Español", "Sí", "2006-10-11", "España"),
                ("Parasite", "Thriller", "Coreano", "Sí", "2019-05-30", "Corea del Sur")
            ]
            c.executemany("INSERT INTO peliculas (nombre, genero, idioma, traduccion, fecha, pais) VALUES (?, ?, ?, ?, ?, ?)", peliculas)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error BD: {e}")
        return False

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verificar_login(username, password):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        password_hash = hash_password(password)
        c.execute("SELECT nombre FROM usuarios WHERE username=? AND password=?", (username, password_hash))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None
    except:
        return None

def obtener_peliculas():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM peliculas")
        peliculas = c.fetchall()
        conn.close()
        return peliculas
    except:
        return []

def agregar_pelicula(nombre, genero, idioma, traduccion, fecha, pais):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO peliculas (nombre, genero, idioma, traduccion, fecha, pais) VALUES (?, ?, ?, ?, ?, ?)",
                 (nombre, genero, idioma, traduccion, fecha, pais))
        conn.commit()
        conn.close()
        return True, "✅ Película agregada"
    except Exception as e:
        return False, f"❌ Error: {e}"

def eliminar_pelicula(pelicula_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM peliculas WHERE id=?", (pelicula_id,))
        conn.commit()
        conn.close()
        return True, "✅ Película eliminada"
    except Exception as e:
        return False, f"❌ Error: {e}"

# INTERFAZ
def login_page():
    st.title("🎬 Sistema de Películas")
    st.subheader("Iniciar Sesión")
    
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
    
    st.info("**Demo:** admin / admin123")

def main_page():
    st.title("🎬 Gestión de Películas")
    st.write(f"👤 Usuario: {st.session_state.nombre}")
    
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()
    
    st.markdown("---")
    
    menu = st.radio("Navegación", ["📋 Ver Películas", "➕ Agregar", "🗑️ Eliminar"], horizontal=True)
    
    if menu == "📋 Ver Películas":
        mostrar_peliculas()
    elif menu == "➕ Agregar":
        agregar_form()
    elif menu == "🗑️ Eliminar":
        eliminar_form()

def mostrar_peliculas():
    st.header("🎬 Lista de Películas")
    
    peliculas = obtener_peliculas()
    
    if not peliculas:
        st.info("No hay películas registradas")
        return
    
    # Mostrar en formato tabla simple
    for pelicula in peliculas:
        id_peli, nombre, genero, idioma, traduccion, fecha, pais = pelicula
        
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(nombre)
                st.write(f"**Género:** {genero} | **Idioma:** {idioma} | **País:** {pais}")
                st.write(f"**Traducción:** {traduccion} | **Fecha:** {fecha}")
            with col2:
                st.write(f"**ID:** {id_peli}")
            st.markdown("---")
    
    # Estadísticas simples
    st.subheader("📊 Estadísticas")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Películas", len(peliculas))
    with col2:
        generos = len(set(p[2] for p in peliculas))
        st.metric("Géneros", generos)
    with col3:
        idiomas = len(set(p[3] for p in peliculas))
        st.metric("Idiomas", idiomas)
    with col4:
        con_traduccion = sum(1 for p in peliculas if p[4] == "Sí")
        st.metric("Con Traducción", con_traduccion)

def agregar_form():
    st.header("➕ Agregar Nueva Película")
    
    with st.form("agregar_pelicula"):
        nombre = st.text_input("Nombre de la película")
        genero = st.text_input("Género")
        idioma = st.text_input("Idioma Original")
        traduccion = st.selectbox("Traducción Disponible", ["Sí", "No"])
        fecha = st.date_input("Fecha de Estreno")
        pais = st.text_input("País de Origen")
        
        if st.form_submit_button("✅ Agregar Película"):
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
                st.warning("Por favor completa todos los campos")

def eliminar_form():
    st.header("🗑️ Eliminar Película")
    
    peliculas = obtener_peliculas()
    
    if not peliculas:
        st.info("No hay películas para eliminar")
        return
    
    # Crear lista de nombres para selección
    nombres_peliculas = [f"{p[0]} - {p[1]}" for p in peliculas]
    
    pelicula_seleccionada = st.selectbox("Selecciona una película para eliminar:", nombres_peliculas)
    
    if st.button("❌ Eliminar Película", type="primary"):
        # Extraer ID de la selección
        pelicula_id = int(pelicula_seleccionada.split(" - ")[0])
        success, msg = eliminar_pelicula(pelicula_id)
        
        if success:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

def main():
    # Inicializar estado
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # Inicializar base de datos
    if init_database():
        if not st.session_state.logged_in:
            login_page()
        else:
            main_page()
    else:
        st.error("No se pudo inicializar la aplicación")

if __name__ == "__main__":
    main()
