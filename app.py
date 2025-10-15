import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import os
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Gestión de Películas",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constantes
DB_FILE = "longlist.db"
ADMIN_DB = "admin_users.db"

# -------------------- FUNCIONES DE BASE DE DATOS --------------------
def crear_db_si_no_existe():
    """Crea la base de datos de películas si no existe"""
    try:
        db_existe = os.path.exists(DB_FILE)
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
        if not db_existe:
            ejemplos = [
                ("Inception", "Ciencia Ficción", "Inglés", "Sí", "2010-07-16", "USA"),
                ("Parasite", "Thriller", "Coreano", "Sí", "2019-05-30", "Corea del Sur"),
                ("Amélie", "Comedia", "Francés", "No", "2001-04-25", "Francia"),
                ("Spirited Away", "Animación", "Japonés", "Sí", "2001-07-20", "Japón"),
                ("El Laberinto del Fauno", "Fantasía", "Español", "Sí", "2006-10-11", "España")
            ]
            c.executemany("""
            INSERT INTO peliculas (nombre, genero, idioma_original, traduccion_disponible, fecha_salida, pais_origen)
            VALUES (?, ?, ?, ?, ?, ?)
            """, ejemplos)
            conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error inicializando base de datos: {e}")

def crear_db_admin():
    """Crea la base de datos de administradores"""
    try:
        conn = sqlite3.connect(ADMIN_DB)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nombre_completo TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        admin_exists = c.execute("SELECT COUNT(*) FROM admins WHERE username='admin'").fetchone()[0]
        if not admin_exists:
            password_hash = hashlib.sha256("admin123".encode()).hexdigest()
            c.execute("INSERT INTO admins (username, password, nombre_completo) VALUES (?, ?, ?)",
                     ("admin", password_hash, "Administrador Principal"))
            conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error inicializando admin DB: {e}")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verificar_login(username, password):
    try:
        conn = sqlite3.connect(ADMIN_DB)
        c = conn.cursor()
        password_hash = hash_password(password)
        result = c.execute("SELECT nombre_completo FROM admins WHERE username=? AND password=?",
                          (username, password_hash)).fetchone()
        conn.close()
        return result[0] if result else None
    except:
        return None

# -------------------- FUNCIONES DE PELÍCULAS --------------------
def obtener_peliculas():
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM peliculas", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()

def agregar_pelicula(nombre, genero, idioma, traduccion, fecha, pais):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
        INSERT INTO peliculas (nombre, genero, idioma_original, traduccion_disponible, fecha_salida, pais_origen)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (nombre, genero, idioma, traduccion, fecha, pais))
        conn.commit()
        conn.close()
        return True, f"Película '{nombre}' agregada correctamente"
    except Exception as e:
        return False, f"Error: {str(e)}"

def actualizar_pelicula(pelicula_id, nombre, genero, idioma, traduccion, fecha, pais):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
        UPDATE peliculas 
        SET nombre=?, genero=?, idioma_original=?, traduccion_disponible=?, fecha_salida=?, pais_origen=?
        WHERE id=?
        """, (nombre, genero, idioma, traduccion, fecha, pais, pelicula_id))
        conn.commit()
        conn.close()
        return True, f"Película '{nombre}' actualizada"
    except Exception as e:
        return False, f"Error: {str(e)}"

def eliminar_pelicula(pelicula_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        nombre = c.execute("SELECT nombre FROM peliculas WHERE id=?", (pelicula_id,)).fetchone()[0]
        c.execute("DELETE FROM peliculas WHERE id=?", (pelicula_id,))
        conn.commit()
        conn.close()
        return True, f"Película '{nombre}' eliminada"
    except Exception as e:
        return False, f"Error: {str(e)}"

# -------------------- FUNCIONES DE ADMINISTRADORES --------------------
def obtener_administradores():
    try:
        conn = sqlite3.connect(ADMIN_DB)
        df = pd.read_sql_query("SELECT id, username, nombre_completo, fecha_creacion FROM admins", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()

def agregar_administrador(nombre_completo, username, password):
    try:
        conn = sqlite3.connect(ADMIN_DB)
        c = conn.cursor()
        password_hash = hash_password(password)
        c.execute("INSERT INTO admins (username, password, nombre_completo) VALUES (?, ?, ?)",
                 (username, password_hash, nombre_completo))
        conn.commit()
        conn.close()
        return True, f"Administrador '{username}' creado correctamente"
    except sqlite3.IntegrityError:
        return False, "El usuario ya existe"
    except Exception as e:
        return False, f"Error: {str(e)}"

def cambiar_password_admin(admin_id, nueva_password):
    try:
        conn = sqlite3.connect(ADMIN_DB)
        c = conn.cursor()
        password_hash = hash_password(nueva_password)
        c.execute("UPDATE admins SET password=? WHERE id=?", (password_hash, admin_id))
        conn.commit()
        conn.close()
        return True, "Contraseña actualizada correctamente"
    except Exception as e:
        return False, f"Error: {str(e)}"

# -------------------- INTERFAZ --------------------
def pagina_login():
    st.title("🎬 Sistema de Gestión de Películas")
    st.subheader("Panel de Administración")
    
    with st.form("login_form"):
        username = st.text_input("👤 Usuario")
        password = st.text_input("🔒 Contraseña", type="password")
        submit = st.form_submit_button("🔓 Iniciar Sesión")
        
        if submit:
            if username and password:
                nombre_completo = verificar_login(username, password)
                if nombre_completo:
                    st.session_state.update({
                        'logged_in': True,
                        'username': username,
                        'nombre_completo': nombre_completo
                    })
                    st.success(f"Bienvenido, {nombre_completo}!")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
            else:
                st.warning("Completa todos los campos")
    
    st.markdown("---")
    st.info("**Credenciales por defecto:**")
    st.info("👤 Usuario: admin | 🔒 Contraseña: admin123")

def pagina_principal():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🎬 Gestión Longlist Películas 2025")
    with col2:
        st.write(f"👤 **Sesión:** {st.session_state.nombre_completo}")
        if st.button("🚪 Cerrar Sesión", type="primary"):
            st.session_state.clear()
            st.rerun()
    
    st.markdown("---")
    
    menu = ["📊 Dashboard", "🎭 Gestión de Películas", "👥 Administradores"]
    opcion = st.sidebar.selectbox("Navegación", menu)
    
    if opcion == "📊 Dashboard":
        mostrar_dashboard()
    elif opcion == "🎭 Gestión de Películas":
        mostrar_gestion_peliculas()
    elif opcion == "👥 Administradores":
        mostrar_gestion_administradores()

def mostrar_dashboard():
    st.header("📊 Dashboard de Películas")
    df = obtener_peliculas()
    
    if df.empty:
        st.warning("No hay datos para mostrar")
        return
    
    # Métricas principales
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: 
        st.metric("Total Películas", len(df))
    with col2: 
        st.metric("Géneros Únicos", df['genero'].nunique())
    with col3: 
        st.metric("Idiomas", df['idioma_original'].nunique())
    with col4: 
        st.metric("Países", df['pais_origen'].nunique())
    with col5: 
        st.metric("Con Traducción", len(df[df['traduccion_disponible'] == 'Sí']))
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        if not df.empty and 'genero' in df.columns:
            genero_count = df['genero'].value_counts()
            fig_genero = px.pie(
                values=genero_count.values,
                names=genero_count.index,
                title="🎭 Distribución por Género",
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            st.plotly_chart(fig_genero, use_container_width=True)
        
        if not df.empty and 'pais_origen' in df.columns:
            pais_count = df['pais_origen'].value_counts().head(10)
            fig_pais = px.bar(
                x=pais_count.values,
                y=pais_count.index,
                orientation='h',
                title="🌍 Top 10 Países de Origen",
                color=pais_count.values,
                color_continuous_scale='viridis'
            )
            fig_pais.update_layout(xaxis_title="Cantidad", yaxis_title="País")
            st.plotly_chart(fig_pais, use_container_width=True)
    
    with col2:
        if not df.empty and 'idioma_original' in df.columns:
            idioma_count = df['idioma_original'].value_counts().head(8)
            fig_idioma = px.bar(
                x=idioma_count.index,
                y=idioma_count.values,
                title="🗣️ Distribución por Idioma (Top 8)",
                color=idioma_count.values,
                color_continuous_scale='plasma'
            )
            fig_idioma.update_layout(xaxis_title="Idioma", yaxis_title="Cantidad")
            st.plotly_chart(fig_idioma, use_container_width=True)
        
        if not df.empty and 'traduccion_disponible' in df.columns:
            trad_count = df['traduccion_disponible'].value_counts()
            fig_trad = px.pie(
                values=trad_count.values,
                names=trad_count.index,
                title="🔄 Disponibilidad de Traducción",
                color_discrete_sequence=['#2ecc71', '#e74c3c']
            )
            st.plotly_chart(fig_trad, use_container_width=True)
    
    # Películas más recientes
    st.subheader("🆕 Películas Más Recientes")
    df_fechas = df.copy()
    try:
        df_fechas['fecha_salida'] = pd.to_datetime(df_fechas['fecha_salida'], errors='coerce')
        df_recientes = df_fechas.dropna(subset=['fecha_salida']).sort_values('fecha_salida', ascending=False).head(5)
        
        for _, pelicula in df_recientes.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{pelicula['nombre']}**")
                with col2:
                    st.write(f"📅 {pelicula['fecha_salida'].strftime('%Y-%m-%d')} | 🎭 {pelicula['genero']}")
                with col3:
                    st.write(f"🌍 {pelicula['pais_origen']}")
                st.markdown("---")
    except:
        st.info("No hay fechas válidas para mostrar")
    
    # Exportar datos
    st.subheader("📁 Exportar Datos")
    if st.button("💾 Descargar CSV"):
        csv = df.to_csv(index=False)
        st.download_button(
            label="⬇️ Descargar CSV",
            data=csv,
            file_name="peliculas.csv",
            mime="text/csv"
        )

def mostrar_gestion_peliculas():
    st.header("🎭 Gestión de Películas")
    
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Agregar Película", "📋 Ver Todas", "✏️ Editar Película", "🗑️ Eliminar Película"])
    
    with tab1:
        st.subheader("Agregar Nueva Película")
        with st.form("agregar_pelicula"):
            col1, col2 = st.columns(2)
            
            with col1:
                nombre = st.text_input("Nombre de la película*")
                genero = st.text_input("Género*")
                idioma = st.text_input("Idioma Original*")
            
            with col2:
                traduccion = st.selectbox("Traducción Disponible*", ["Sí", "No"])
                fecha = st.date_input("Fecha de Salida*")
                pais = st.text_input("País de Origen*")
            
            if st.form_submit_button("✅ Agregar Película"):
                if all([nombre, genero, idioma, pais]):
                    success, message = agregar_pelicula(
                        nombre, genero, idioma, traduccion, 
                        fecha.strftime("%Y-%m-%d"), pais
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.warning("Por favor completa todos los campos obligatorios (*)")
    
    with tab2:
        st.subheader("Todas las Películas")
        df = obtener_peliculas()
        
        if not df.empty:
            # Filtros
            col1, col2, col3 = st.columns(3)
            with col1:
                filtro_genero = st.selectbox("Filtrar por género", ["Todos"] + list(df['genero'].unique()))
            with col2:
                filtro_idioma = st.selectbox("Filtrar por idioma", ["Todos"] + list(df['idioma_original'].unique()))
            with col3:
                filtro_traduccion = st.selectbox("Filtrar por traducción", ["Todos", "Sí", "No"])
            
            # Aplicar filtros
            df_filtrado = df.copy()
            if filtro_genero != "Todos":
                df_filtrado = df_filtrado[df_filtrado['genero'] == filtro_genero]
            if filtro_idioma != "Todos":
                df_filtrado = df_filtrado[df_filtrado['idioma_original'] == filtro_idioma]
            if filtro_traduccion != "Todos":
                df_filtrado = df_filtrado[df_filtrado['traduccion_disponible'] == filtro_traduccion]
            
            st.dataframe(df_filtrado, use_container_width=True)
            
            # Estadísticas rápidas
            st.subheader("📈 Estadísticas Rápidas")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Películas mostradas", len(df_filtrado))
            with col2:
                st.metric("Géneros", df_filtrado['genero'].nunique())
            with col3:
                st.metric("Idiomas", df_filtrado['idioma_original'].nunique())
            with col4:
                st.metric("Países", df_filtrado['pais_origen'].nunique())
        else:
            st.info("No hay películas registradas")
    
    with tab3:
        st.subheader("Editar Película Existente")
        df = obtener_peliculas()
        
        if not df.empty:
            pelicula_seleccionada = st.selectbox(
                "Selecciona una película para editar",
                df['nombre'].values
            )
            
            pelicula_data = df[df['nombre'] == pelicula_seleccionada].iloc[0]
            
            with st.form("editar_pelicula"):
                col1, col2 = st.columns(2)
                
                with col1:
                    nuevo_nombre = st.text_input("Nombre*", value=pelicula_data['nombre'])
                    nuevo_genero = st.text_input("Género*", value=pelicula_data['genero'])
                    nuevo_idioma = st.text_input("Idioma Original*", value=pelicula_data['idioma_original'])
                
                with col2:
                    nueva_traduccion = st.selectbox(
                        "Traducción Disponible*", 
                        ["Sí", "No"],
                        index=0 if pelicula_data['traduccion_disponible'] == 'Sí' else 1
                    )
                    try:
                        fecha_default = datetime.strptime(pelicula_data['fecha_salida'], "%Y-%m-%d") if pelicula_data['fecha_salida'] else datetime.now()
                    except:
                        fecha_default = datetime.now()
                    
                    nueva_fecha = st.date_input("Fecha de Salida*", value=fecha_default)
                    nuevo_pais = st.text_input("País de Origen*", value=pelicula_data['pais_origen'])
                
                if st.form_submit_button("💾 Actualizar Película"):
                    if all([nuevo_nombre, nuevo_genero, nuevo_idioma, nuevo_pais]):
                        success, message = actualizar_pelicula(
                            pelicula_data['id'],
                            nuevo_nombre, nuevo_genero, nuevo_idioma,
                            nueva_traduccion, nueva_fecha.strftime("%Y-%m-%d"), nuevo_pais
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.warning("Por favor completa todos los campos obligatorios (*)")
        else:
            st.info("No hay películas para editar")
    
    with tab4:
        st.subheader("Eliminar Película")
        df = obtener_peliculas()
        
        if not df.empty:
            pelicula_eliminar = st.selectbox(
                "Selecciona una película para eliminar",
                df['nombre'].values,
                key="eliminar_select"
            )
            
            pelicula_data = df[df['nombre'] == pelicula_eliminar].iloc[0]
            
            # Mostrar información de la película
            st.warning("⚠️ **Información de la película seleccionada:**")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**ID:** {pelicula_data['id']}")
                st.write(f"**Género:** {pelicula_data['genero']}")
                st.write(f"**Idioma:** {pelicula_data['idioma_original']}")
            with col2:
                st.write(f"**Traducción:** {pelicula_data['traduccion_disponible']}")
                st.write(f"**Fecha:** {pelicula_data['fecha_salida']}")
                st.write(f"**País:** {pelicula_data['pais_origen']}")
            
            if st.button("🗑️ Eliminar Película", type="primary"):
                success, message = eliminar_pelicula(pelicula_data['id'])
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        else:
            st.info("No hay películas para eliminar")

def mostrar_gestion_administradores():
    st.header("👥 Gestión de Administradores")
    
    tab1, tab2 = st.tabs(["➕ Agregar Administrador", "📋 Administradores Registrados"])
    
    with tab1:
        st.subheader("Agregar Nuevo Administrador")
        with st.form("agregar_admin"):
            nombre_completo = st.text_input("Nombre Completo*")
            username = st.text_input("Usuario*")
            password = st.text_input("Contraseña*", type="password")
            confirm_password = st.text_input("Confirmar Contraseña*", type="password")
            
            if st.form_submit_button("✅ Crear Administrador"):
                if all([nombre_completo, username, password, confirm_password]):
                    if password != confirm_password:
                        st.error("Las contraseñas no coinciden")
                    elif len(password) < 6:
                        st.warning("La contraseña debe tener al menos 6 caracteres")
                    elif len(username) < 3:
                        st.warning("El usuario debe tener al menos 3 caracteres")
                    else:
                        success, message = agregar_administrador(nombre_completo, username, password)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                else:
                    st.warning("Todos los campos son obligatorios (*)")
    
    with tab2:
        st.subheader("Administradores Registrados")
        df_admins = obtener_administradores()
        
        if not df_admins.empty:
            st.dataframe(df_admins, use_container_width=True)
            
            # Cambiar contraseña
            st.subheader("🔑 Cambiar Contraseña")
            admin_seleccionado = st.selectbox(
                "Selecciona un administrador",
                df_admins['username'].values
            )
            
            with st.form("cambiar_password"):
                nueva_password = st.text_input("Nueva Contraseña*", type="password")
                confirmar_password = st.text_input("Confirmar Contraseña*", type="password")
                
                if st.form_submit_button("💾 Cambiar Contraseña"):
                    if nueva_password and confirmar_password:
                        if nueva_password != confirmar_password:
                            st.error("Las contraseñas no coinciden")
                        elif len(nueva_password) < 6:
                            st.warning("La contraseña debe tener al menos 6 caracteres")
                        else:
                            admin_id = df_admins[df_admins['username'] == admin_seleccionado].iloc[0]['id']
                            success, message = cambiar_password_admin(admin_id, nueva_password)
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                    else:
                        st.warning("Completa ambos campos")
        else:
            st.info("No hay administradores registrados")

def main():
    # Inicializar bases de datos
    crear_db_si_no_existe()
    crear_db_admin()
    
    # Inicializar estado de sesión
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # Mostrar página correspondiente
    if not st.session_state.logged_in:
        pagina_login()
    else:
        pagina_principal()

if __name__ == "__main__":
    main()