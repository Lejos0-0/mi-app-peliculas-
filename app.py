import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import os
from datetime import datetime
import io

# Configuración
st.set_page_config(
    page_title="Sistema de Películas",
    page_icon="🎬",
    layout="wide"
)

# Constantes
DB_FILE = "peliculas.db"

def init_database():
    """Inicializar base de datos con tablas mejoradas"""
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
                pais TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario_creacion TEXT
            )
        ''')
        
        # Tabla de usuarios con roles
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                nombre TEXT,
                rol TEXT DEFAULT 'usuario',
                activo INTEGER DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Usuario admin por defecto
        c.execute("SELECT COUNT(*) FROM usuarios WHERE username='admin'")
        if c.fetchone()[0] == 0:
            password_hash = hash_password("admin123")
            c.execute("INSERT INTO usuarios (username, password, nombre, rol) VALUES (?, ?, ?, ?)",
                     ("admin", password_hash, "Administrador Principal", "admin"))
        
        # Usuario viewer por defecto
        c.execute("SELECT COUNT(*) FROM usuarios WHERE username='viewer'")
        if c.fetchone()[0] == 0:
            password_hash = hash_password("viewer123")
            c.execute("INSERT INTO usuarios (username, password, nombre, rol) VALUES (?, ?, ?, ?)",
                     ("viewer", password_hash, "Usuario Viewer", "viewer"))
        
        # Datos de ejemplo
        c.execute("SELECT COUNT(*) FROM peliculas")
        if c.fetchone()[0] == 0:
            peliculas = [
                ("Inception", "Ciencia Ficción", "Inglés", "Sí", "2010-07-16", "USA", "admin"),
                ("El Laberinto del Fauno", "Fantasía", "Español", "Sí", "2006-10-11", "España", "admin"),
                ("Parasite", "Thriller", "Coreano", "Sí", "2019-05-30", "Corea del Sur", "admin")
            ]
            c.executemany("INSERT INTO peliculas (nombre, genero, idioma, traduccion, fecha, pais, usuario_creacion) VALUES (?, ?, ?, ?, ?, ?, ?)", peliculas)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error BD: {e}")
        return False

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verificar_login(username, password):
    """Verificar login y obtener datos del usuario"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        password_hash = hash_password(password)
        c.execute("SELECT nombre, rol FROM usuarios WHERE username=? AND password=? AND activo=1", 
                 (username, password_hash))
        result = c.fetchone()
        conn.close()
        
        if result:
            return {
                'nombre': result[0],
                'rol': result[1],
                'username': username
            }
        return None
    except:
        return None

def obtener_peliculas():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM peliculas ORDER BY fecha_creacion DESC")
        peliculas = c.fetchall()
        conn.close()
        return peliculas
    except:
        return []

def agregar_pelicula(nombre, genero, idioma, traduccion, fecha, pais, usuario):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO peliculas (nombre, genero, idioma, traduccion, fecha, pais, usuario_creacion) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (nombre, genero, idioma, traduccion, fecha, pais, usuario))
        conn.commit()
        conn.close()
        return True, "✅ Película agregada"
    except Exception as e:
        return False, f"❌ Error: {e}"

def eliminar_pelicula(pelicula_id, usuario_actual):
    """Eliminar película con verificación de permisos"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Verificar si el usuario es admin o el creador de la película
        c.execute("SELECT usuario_creacion FROM peliculas WHERE id=?", (pelicula_id,))
        resultado = c.fetchone()
        
        if not resultado:
            return False, "❌ Película no encontrada"
        
        usuario_creacion = resultado[0]
        rol_actual = st.session_state.user_data['rol']
        
        # Solo admin puede eliminar cualquier película, usuarios solo las suyas
        if rol_actual == 'admin' or usuario_actual == usuario_creacion:
            c.execute("DELETE FROM peliculas WHERE id=?", (pelicula_id,))
            conn.commit()
            conn.close()
            return True, "✅ Película eliminada"
        else:
            conn.close()
            return False, "❌ No tienes permisos para eliminar esta película"
            
    except Exception as e:
        return False, f"❌ Error: {e}"

# ==================== GESTIÓN DE USUARIOS ====================
def obtener_usuarios():
    """Obtener lista de todos los usuarios (solo admin)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, username, nombre, rol, activo, fecha_creacion FROM usuarios ORDER BY fecha_creacion DESC")
        usuarios = c.fetchall()
        conn.close()
        return usuarios
    except:
        return []

def crear_usuario(username, password, nombre, rol):
    """Crear nuevo usuario"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        password_hash = hash_password(password)
        c.execute("INSERT INTO usuarios (username, password, nombre, rol) VALUES (?, ?, ?, ?)",
                 (username, password_hash, nombre, rol))
        conn.commit()
        conn.close()
        return True, "✅ Usuario creado correctamente"
    except sqlite3.IntegrityError:
        return False, "❌ El nombre de usuario ya existe"
    except Exception as e:
        return False, f"❌ Error: {e}"

def actualizar_usuario(user_id, username, nombre, rol, activo):
    """Actualizar usuario existente"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE usuarios SET username=?, nombre=?, rol=?, activo=? WHERE id=?",
                 (username, nombre, rol, activo, user_id))
        conn.commit()
        conn.close()
        return True, "✅ Usuario actualizado correctamente"
    except sqlite3.IntegrityError:
        return False, "❌ El nombre de usuario ya existe"
    except Exception as e:
        return False, f"❌ Error: {e}"

def cambiar_password_usuario(user_id, nueva_password):
    """Cambiar contraseña de usuario"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        password_hash = hash_password(nueva_password)
        c.execute("UPDATE usuarios SET password=? WHERE id=?", (password_hash, user_id))
        conn.commit()
        conn.close()
        return True, "✅ Contraseña actualizada correctamente"
    except Exception as e:
        return False, f"❌ Error: {e}"

def gestion_usuarios():
    """Interfaz de gestión de usuarios (solo para admin)"""
    st.header("👥 Gestión de Usuarios")
    
    if st.session_state.user_data['rol'] != 'admin':
        st.error("❌ Solo los administradores pueden acceder a esta sección")
        return
    
    tab1, tab2, tab3 = st.tabs(["📋 Lista de Usuarios", "➕ Crear Usuario", "🔑 Cambiar Contraseñas"])
    
    with tab1:
        st.subheader("Usuarios Registrados")
        
        usuarios = obtener_usuarios()
        if not usuarios:
            st.info("No hay usuarios registrados")
            return
        
        for usuario in usuarios:
            user_id, username, nombre, rol, activo, fecha_creacion = usuario
            
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                
                with col1:
                    st.write(f"**{nombre}**")
                    st.write(f"Usuario: {username}")
                
                with col2:
                    st.write(f"Rol: **{rol}**")
                    estado = "🟢 Activo" if activo == 1 else "🔴 Inactivo"
                    st.write(f"Estado: {estado}")
                
                with col3:
                    st.write(f"Creado: {fecha_creacion[:10]}")
                
                with col4:
                    with st.expander("Editar"):
                        with st.form(f"editar_usuario_{user_id}"):
                            nuevo_username = st.text_input("Usuario", value=username, key=f"user_{user_id}")
                            nuevo_nombre = st.text_input("Nombre completo", value=nombre, key=f"name_{user_id}")
                            nuevo_rol = st.selectbox("Rol", ["admin", "editor", "viewer"], 
                                                   index=["admin", "editor", "viewer"].index(rol), 
                                                   key=f"rol_{user_id}")
                            nuevo_activo = st.selectbox("Estado", ["Activo", "Inactivo"],
                                                      index=0 if activo == 1 else 1,
                                                      key=f"activo_{user_id}")
                            
                            if st.form_submit_button("💾 Actualizar"):
                                success, msg = actualizar_usuario(
                                    user_id, nuevo_username, nuevo_nombre, nuevo_rol, 
                                    1 if nuevo_activo == "Activo" else 0
                                )
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                
                st.markdown("---")
    
    with tab2:
        st.subheader("Crear Nuevo Usuario")
        
        with st.form("crear_usuario"):
            col1, col2 = st.columns(2)
            
            with col1:
                nuevo_username = st.text_input("Usuario*")
                nuevo_nombre = st.text_input("Nombre completo*")
            
            with col2:
                nuevo_rol = st.selectbox("Rol*", ["viewer", "editor", "admin"])
                nueva_password = st.text_input("Contraseña*", type="password")
                confirm_password = st.text_input("Confirmar contraseña*", type="password")
            
            if st.form_submit_button("👤 Crear Usuario"):
                if all([nuevo_username, nuevo_nombre, nueva_password, confirm_password]):
                    if nueva_password != confirm_password:
                        st.error("❌ Las contraseñas no coinciden")
                    elif len(nueva_password) < 6:
                        st.warning("⚠️ La contraseña debe tener al menos 6 caracteres")
                    else:
                        success, msg = crear_usuario(nuevo_username, nueva_password, nuevo_nombre, nuevo_rol)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    st.warning("⚠️ Completa todos los campos obligatorios")
    
    with tab3:
        st.subheader("Cambiar Contraseñas")
        
        usuarios = obtener_usuarios()
        if usuarios:
            usuario_seleccionado = st.selectbox(
                "Seleccionar usuario",
                [f"{u[0]} - {u[1]} ({u[2]})" for u in usuarios],
                key="cambiar_pass"
            )
            
            user_id = int(usuario_seleccionado.split(" - ")[0])
            
            with st.form("cambiar_password"):
                nueva_password = st.text_input("Nueva contraseña*", type="password")
                confirm_password = st.text_input("Confirmar contraseña*", type="password")
                
                if st.form_submit_button("🔑 Cambiar Contraseña"):
                    if nueva_password and confirm_password:
                        if nueva_password != confirm_password:
                            st.error("❌ Las contraseñas no coinciden")
                        elif len(nueva_password) < 6:
                            st.warning("⚠️ La contraseña debe tener al menos 6 caracteres")
                        else:
                            success, msg = cambiar_password_usuario(user_id, nueva_password)
                            if success:
                                st.success(msg)
                            else:
                                st.error(msg)
                    else:
                        st.warning("⚠️ Completa ambos campos")

# ==================== FUNCIONES DE ACTUALIZACIÓN MASIVA MEJORADAS ====================
def conectar_db():
    return sqlite3.connect(DB_FILE)

def limpiar_tabla():
    """Solo admin puede limpiar la tabla"""
    if st.session_state.user_data['rol'] != 'admin':
        return "❌ Solo los administradores pueden limpiar la tabla"
    
    conn = conectar_db()
    c = conn.cursor()
    c.execute("DELETE FROM peliculas")
    conn.commit()
    conn.close()
    return "🗑️ Tabla limpiada correctamente"

def importar_desde_csv(archivo_csv, usuario):
    """Importar datos desde archivo CSV - VERSIÓN MEJORADA"""
    try:
        # Leer el archivo CSV
        df = pd.read_csv(archivo_csv)
        
        conn = conectar_db()
        c = conn.cursor()
        
        registros_procesados = 0
        errores = []
        
        for index, fila in df.iterrows():
            try:
                # Mapeo flexible de columnas
                nombre = ""
                genero = ""
                idioma = ""
                traduccion = "No"
                fecha = ""
                pais = ""
                
                # Buscar en todas las columnas posibles
                for col_name in df.columns:
                    col_value = str(fila[col_name]) if pd.notna(fila[col_name]) else ""
                    col_lower = col_name.lower()
                    
                    if any(keyword in col_lower for keyword in ['nombre', 'name', 'title', 'pelicula', 'movie']):
                        nombre = col_value
                    elif any(keyword in col_lower for keyword in ['genero', 'genre', 'categoria', 'category']):
                        genero = col_value
                    elif any(keyword in col_lower for keyword in ['idioma', 'language', 'lenguaje']):
                        idioma = col_value
                    elif any(keyword in col_lower for keyword in ['traduccion', 'translation', 'subtitulos']):
                        traduccion = "Sí" if any(keyword in col_value.lower() for keyword in ['sí', 'si', 'yes', 'true', '1']) else "No"
                    elif any(keyword in col_lower for keyword in ['fecha', 'date', 'año', 'year', 'estreno']):
                        fecha = col_value
                    elif any(keyword in col_lower for keyword in ['pais', 'country', 'origen', 'origin']):
                        pais = col_value
                
                # Validar datos esenciales
                if nombre and genero:
                    # Limpiar datos
                    nombre = nombre.strip()
                    genero = genero.strip()
                    idioma = idioma.strip() if idioma else "Desconocido"
                    pais = pais.strip() if pais else "Desconocido"
                    
                    c.execute(
                        "INSERT INTO peliculas (nombre, genero, idioma, traduccion, fecha, pais, usuario_creacion) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (nombre, genero, idioma, traduccion, fecha, pais, usuario)
                    )
                    registros_procesados += 1
                else:
                    errores.append(f"Fila {index+1}: Datos insuficientes (nombre: '{nombre}', género: '{genero}')")
                    
            except Exception as e:
                errores.append(f"Fila {index+1}: Error - {str(e)}")
        
        conn.commit()
        conn.close()
        
        return True, f"✅ {registros_procesados} registros importados correctamente", errores
        
    except Exception as e:
        return False, f"❌ Error en importación: {str(e)}", []

def exportar_a_csv():
    try:
        conn = conectar_db()
        df = pd.read_sql_query("SELECT * FROM peliculas", conn)
        conn.close()
        
        if df.empty:
            return None, "No hay datos para exportar"
        
        csv_data = df.to_csv(index=False, encoding='utf-8')
        return csv_data, f"✅ {len(df)} registros listos para exportar"
        
    except Exception as e:
        return None, f"❌ Error en exportación: {str(e)}"

def actualizar_pelicula_masiva():
    st.header("🔄 Herramientas de Actualización Masiva")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📤 Exportar CSV", "📥 Importar CSV", "🔄 Actualizar Rápido", "🗑️ Limpiar Datos"])
    
    with tab1:
        st.subheader("Exportar Datos a CSV")
        
        if st.button("📥 Generar Archivo CSV"):
            csv_data, mensaje = exportar_a_csv()
            
            if csv_data:
                st.download_button(
                    label="⬇️ Descargar CSV Completo",
                    data=csv_data,
                    file_name=f"peliculas_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
                st.success(mensaje)
            else:
                st.error(mensaje)
        
        peliculas = obtener_peliculas()
        if peliculas:
            st.subheader("📋 Vista Previa de Datos")
            df_preview = pd.DataFrame(peliculas, columns=['ID', 'Nombre', 'Género', 'Idioma', 'Traducción', 'Fecha', 'País', 'Fecha_Creacion', 'Usuario'])
            st.dataframe(df_preview.head(10))
            st.write(f"Total de películas en base de datos: {len(peliculas)}")
    
    with tab2:
        st.subheader("📥 Importar Datos desde CSV")
        
        # Verificar permisos
        if st.session_state.user_data['rol'] not in ['admin', 'editor']:
            st.error("❌ Solo administradores y editores pueden importar datos")
            return
        
        st.info("""
        **📝 Formato de CSV aceptado:**
        - El sistema detectará automáticamente las columnas con estos nombres (o similares):
        - **nombre, título, pelicula** → Nombre de la película
        - **genero, género, categoria** → Género cinematográfico  
        - **idioma, lenguaje, language** → Idioma original
        - **traduccion, traducción, subtitulos** → ¿Tiene traducción? (Sí/No)
        - **fecha, date, estreno, año** → Fecha de estreno
        - **pais, país, country, origen** → País de origen
        """)
        
        # Inicializar estado del archivo en session_state
        if 'archivo_csv_cargado' not in st.session_state:
            st.session_state.archivo_csv_cargado = None
            st.session_state.df_preview = None
        
        # File uploader
        archivo_csv = st.file_uploader(
            "Selecciona un archivo CSV", 
            type=['csv'], 
            key="csv_uploader"
        )
        
        # Botón para cargar el archivo
        if archivo_csv is not None:
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("📁 Cargar CSV", type="primary"):
                    try:
                        # Guardar el archivo en session_state
                        st.session_state.archivo_csv_cargado = archivo_csv
                        # Leer el CSV para vista previa
                        st.session_state.df_preview = pd.read_csv(archivo_csv)
                        st.success("✅ Archivo cargado correctamente")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al cargar el archivo: {str(e)}")
            
            with col2:
                if st.session_state.archivo_csv_cargado:
                    st.success(f"📄 Archivo cargado: {st.session_state.archivo_csv_cargado.name}")
        
        # Mostrar información del archivo cargado
        if st.session_state.archivo_csv_cargado is not None and st.session_state.df_preview is not None:
            st.subheader("👀 Vista previa del archivo cargado")
            st.dataframe(st.session_state.df_preview.head())
            
            st.write("**🔍 Columnas detectadas:**")
            st.write(list(st.session_state.df_preview.columns))
            
            st.write(f"**📊 Total de filas:** {len(st.session_state.df_preview)}")
            
            # Opciones de importación
            st.subheader("⚙️ Opciones de Importación")
            opciones_importacion = st.radio(
                "Modo de importación:",
                ["➕ Agregar nuevos registros", "🔄 Reemplazar todos los datos"],
                key="import_mode"
            )
            
            # Botón de importación
            if st.button("🚀 Importar a Base de Datos", type="primary", key="import_btn"):
                with st.spinner("📤 Importando datos a la base de datos..."):
                    # Limpiar tabla si es necesario
                    if "Reemplazar" in opciones_importacion:
                        if st.session_state.user_data['rol'] == 'admin':
                            resultado_limpieza = limpiar_tabla()
                            st.info(resultado_limpieza)
                        else:
                            st.error("❌ Solo los administradores pueden reemplazar todos los datos")
                            return
                    
                    # Resetear el archivo para lectura
                    st.session_state.archivo_csv_cargado.seek(0)
                    
                    # Ejecutar importación
                    success, mensaje, errores = importar_desde_csv(
                        st.session_state.archivo_csv_cargado, 
                        st.session_state.user_data['username']
                    )
                    
                    if success:
                        st.success(mensaje)
                        if errores:
                            st.warning(f"⚠️ Se encontraron {len(errores)} errores durante la importación")
                            with st.expander("📋 Ver detalles de errores"):
                                for error in errores[:10]:
                                    st.error(error)
                                if len(errores) > 10:
                                    st.info(f"... y {len(errores) - 10} errores más")
                        
                        # Limpiar el estado después de importar exitosamente
                        st.session_state.archivo_csv_cargado = None
                        st.session_state.df_preview = None
                    else:
                        st.error(mensaje)
                    
                    # Forzar rerun para actualizar la interfaz
                    st.rerun()
            
            # Botón para limpiar el archivo cargado
            if st.button("🗑️ Limpiar Archivo Cargado"):
                st.session_state.archivo_csv_cargado = None
                st.session_state.df_preview = None
                st.success("✅ Archivo eliminado de la memoria")
                st.rerun()
    
    with tab3:
        st.subheader("🔄 Actualización Rápida por Texto")
        
        if st.session_state.user_data['rol'] not in ['admin', 'editor']:
            st.error("❌ Solo administradores y editores pueden agregar películas")
        else:
            st.write("""
            **📝 Formato por línea:** 
            `nombre;género;idioma;traducción;fecha;país`
            
            **Ejemplo:**
            ```
            El Padrino;Drama;Inglés;Sí;1972-03-24;USA
            Toy Story;Animación;Inglés;Sí;1995-11-22;USA
            ```
            """)
            
            with st.form("agregar_rapido"):
                datos_texto = st.text_area(
                    "Ingresa los datos (una película por línea):", 
                    height=200,
                    placeholder="Ejemplo:\nEl Padrino;Drama;Inglés;Sí;1972-03-24;USA\nToy Story;Animación;Inglés;Sí;1995-11-22;USA"
                )
                
                if st.form_submit_button("➕ Agregar Películas"):
                    if datos_texto:
                        lineas = datos_texto.strip().split('\n')
                        conn = conectar_db()
                        c = conn.cursor()
                        
                        agregadas = 0
                        errores = []
                        
                        for i, linea in enumerate(lineas):
                            try:
                                datos = [d.strip() for d in linea.split(';')]
                                if len(datos) == 6:
                                    nombre, genero, idioma, traduccion, fecha, pais = datos
                                    if nombre and genero:
                                        c.execute(
                                            "INSERT INTO peliculas (nombre, genero, idioma, traduccion, fecha, pais, usuario_creacion) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                            (nombre, genero, idioma, traduccion, fecha, pais, st.session_state.user_data['username'])
                                        )
                                        agregadas += 1
                                    else:
                                        errores.append(f"Línea {i+1}: Nombre y género requeridos")
                                else:
                                    errores.append(f"Línea {i+1}: Formato incorrecto (se esperaban 6 campos separados por ';')")
                                    
                            except Exception as e:
                                errores.append(f"Línea {i+1}: {str(e)}")
                        
                        conn.commit()
                        conn.close()
                        
                        st.success(f"✅ {agregadas} películas agregadas correctamente")
                        if errores:
                            st.warning(f"❌ {len(errores)} líneas con errores:")
                            for error in errores[:5]:
                                st.write(f"• {error}")
                    else:
                        st.warning("⚠️ Ingresa al menos una película")
    
    with tab4:
        st.subheader("🗑️ Herramientas de Limpieza")
        
        if st.session_state.user_data['rol'] != 'admin':
            st.error("❌ Solo los administradores pueden acceder a esta sección")
        else:
            st.warning("⚠️ Zona de peligro - Acciones no reversibles")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🧹 Limpiar Todos los Datos", type="primary"):
                    if st.checkbox("✅ Confirmar eliminación de TODOS los datos"):
                        mensaje = limpiar_tabla()
                        st.success(mensaje)
                        st.rerun()
            
            with col2:
                if st.button("📊 Generar Datos de Ejemplo"):
                    conn = conectar_db()
                    c = conn.cursor()
                    
                    ejemplos = [
                        ("El Señor de los Anillos", "Fantasía", "Inglés", "Sí", "2001-12-19", "USA", "admin"),
                        ("Matrix", "Ciencia Ficción", "Inglés", "Sí", "1999-03-31", "USA", "admin"),
                        ("Coco", "Animación", "Español", "Sí", "2017-10-27", "México", "admin")
                    ]
                    
                    c.executemany(
                        "INSERT INTO peliculas (nombre, genero, idioma, traduccion, fecha, pais, usuario_creacion) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        ejemplos
                    )
                    conn.commit()
                    conn.close()
                    st.success("✅ Películas de ejemplo agregadas")
                    st.rerun()

# ==================== INTERFAZ PRINCIPAL MEJORADA ====================
def pagina_login():
    st.title("🎬 Sistema de Gestión de Películas")
    st.subheader("Inicio de Sesión")
    
    with st.form("login"):
        user = st.text_input("Usuario")
        pwd = st.text_input("Contraseña", type="password")
        
        if st.form_submit_button("Entrar"):
            if user and pwd:
                user_data = verificar_login(user, pwd)
                if user_data:
                    st.session_state.update({
                        'logged_in': True,
                        'user_data': user_data
                    })
                    st.success(f"👋 Bienvenido {user_data['nombre']} ({user_data['rol']})!")
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas o usuario inactivo")
            else:
                st.warning("⚠️ Completa ambos campos")
    
    st.info("""
    **👤 Usuarios de prueba:**
    - **Admin:** usuario: `admin` | contraseña: `admin123`
    - **Viewer:** usuario: `viewer` | contraseña: `viewer123`
    """)

def pagina_principal():
    st.title("🎬 Gestión de Películas")
    
    user_data = st.session_state.user_data
    st.write(f"👤 **Usuario:** {user_data['nombre']} | **Rol:** {user_data['rol']} | **Username:** {user_data['username']}")
    
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()
    
    st.markdown("---")
    
    # Navegación según el rol
    if user_data['rol'] == 'admin':
        opciones = ["📊 Dashboard", "🎭 Ver Películas", "➕ Agregar Individual", "🔄 Actualización Masiva", "👥 Gestión de Usuarios"]
    elif user_data['rol'] == 'editor':
        opciones = ["📊 Dashboard", "🎭 Ver Películas", "➕ Agregar Individual", "🔄 Actualización Masiva"]
    else:  # viewer
        opciones = ["📊 Dashboard", "🎭 Ver Películas"]
    
    opcion = st.radio("Navegación", opciones, horizontal=True)
    
    if opcion == "📊 Dashboard":
        mostrar_dashboard()
    elif opcion == "🎭 Ver Películas":
        mostrar_peliculas()
    elif opcion == "➕ Agregar Individual":
        agregar_pelicula_form()
    elif opcion == "🔄 Actualización Masiva":
        actualizar_pelicula_masiva()
    elif opcion == "👥 Gestión de Usuarios":
        gestion_usuarios()

def mostrar_dashboard():
    st.header("📊 Dashboard")
    
    peliculas = obtener_peliculas()
    if not peliculas:
        st.info("📝 No hay películas registradas")
        return
    
    # Métricas principales
    st.subheader("📈 Métricas Principales")
    col1, col2, col3, col4 = st.columns(4)
    with col1: 
        st.metric("Total Películas", len(peliculas))
    with col2: 
        generos = len(set(p[2] for p in peliculas))
        st.metric("Géneros Diferentes", generos)
    with col3: 
        idiomas = len(set(p[3] for p in peliculas))
        st.metric("Idiomas", idiomas)
    with col4: 
        con_traduccion = sum(1 for p in peliculas if p[4] == "Sí")
        st.metric("Con Traducción", con_traduccion)
    
    # Últimas películas
    st.subheader("🎬 Últimas Películas Agregadas")
    for pelicula in peliculas[:5]:
        id_peli, nombre, genero, idioma, traduccion, fecha, pais, fecha_creacion, usuario = pelicula
        
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{nombre}**")
                st.write(f"*{genero}* | 🌍 {pais} | 🗣️ {idioma} | 🔄 {traduccion}")
            with col2:
                st.write(f"📅 {fecha}")
                st.write(f"👤 {usuario}")
            st.markdown("---")

def mostrar_peliculas():
    st.header("🎭 Lista Completa de Películas")
    
    peliculas = obtener_peliculas()
    
    if not peliculas:
        st.info("📝 No hay películas registradas")
        return
    
    # Búsqueda
    busqueda = st.text_input("🔍 Buscar por nombre, género o país")
    if busqueda:
        peliculas = [p for p in peliculas if busqueda.lower() in str(p[1]).lower() or 
                    busqueda.lower() in str(p[2]).lower() or 
                    busqueda.lower() in str(p[6]).lower()]
    
    # Mostrar películas con opción de eliminar
    for pelicula in peliculas:
        id_peli, nombre, genero, idioma, traduccion, fecha, pais, fecha_creacion, usuario = pelicula
        
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.subheader(nombre)
                st.write(f"**Género:** {genero} | **Idioma:** {idioma} | **País:** {pais}")
            
            with col2:
                st.write(f"**Traducción:** {traduccion} | **Fecha:** {fecha}")
                st.write(f"**Agregado por:** {usuario}")
            
            with col3:
                st.write(f"**ID:** {id_peli}")
                
                # Botón de eliminar (solo para admin o el creador)
                user_data = st.session_state.user_data
                if user_data['rol'] == 'admin' or user_data['username'] == usuario:
                    if st.button("🗑️ Eliminar", key=f"del_{id_peli}"):
                        success, msg = eliminar_pelicula(id_peli, user_data['username'])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
            
            st.markdown("---")
    
    st.info(f"📊 Mostrando {len(peliculas)} películas")

def agregar_pelicula_form():
    st.header("➕ Agregar Película Individual")
    
    # Verificar permisos
    if st.session_state.user_data['rol'] not in ['admin', 'editor']:
        st.error("❌ Solo administradores y editores pueden agregar películas")
        return
    
    with st.form("agregar_pelicula"):
        nombre = st.text_input("Nombre de la película*")
        genero = st.text_input("Género*")
        idioma = st.text_input("Idioma Original*")
        traduccion = st.selectbox("Traducción Disponible*", ["Sí", "No"])
        fecha = st.date_input("Fecha de Estreno*")
        pais = st.text_input("País de Origen*")
        
        if st.form_submit_button("✅ Agregar Película"):
            if all([nombre, genero, idioma, pais]):
                success, msg = agregar_pelicula(
                    nombre, genero, idioma, traduccion,
                    fecha.strftime("%Y-%m-%d"), pais,
                    st.session_state.user_data['username']
                )
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.warning("⚠️ Completa todos los campos obligatorios (*)")

def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not init_database():
        st.error("❌ Error crítico: No se pudieron inicializar las bases de datos")
        return
    
    if not st.session_state.logged_in:
        pagina_login()
    else:
        pagina_principal()

if __name__ == "__main__":
    main()
