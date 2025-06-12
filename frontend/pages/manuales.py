import streamlit as st
from streamlit.components.v1 import html # Mantener por si generas otros componentes HTML en el futuro, aunque no se usa para la TOC
import re
from pathlib import Path
from typing import List, Dict, Tuple
from menu import generarMenu

# --- Configuración de la Página ---
# Configura la página de Streamlit para usar el ancho completo y ocultar el sidebar predeterminado.
st.set_page_config(layout="wide")

# Obtener la ruta del directorio actual del script
current_dir = Path(__file__).parent

# Función para verificar el estado de login
def check_login():
    return 'logged_in' in st.session_state and st.session_state.logged_in

# Verificar si el usuario está logueado
if not check_login():
    st.error("Debes iniciar sesión para acceder a esta página.")
    st.query_params = {}
    st.rerun()

# Configuración de la página
if 'user_info' in st.session_state:
    """ """
    #st.write(f"Bienvenido, {st.session_state.user_info['full_name']}!")
else:
    st.error("Información de usuario no disponible.")
    st.stop()

# Generar el menú con botón de salir
if generarMenu():
    btnSalir = st.button("Salir")
    if btnSalir:
        st.session_state.clear()
        st.rerun()

# Título principal del dashboard

# Título principal con estilo
st.markdown("""
    <div style='text-align: center; padding: 20px; background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); border-radius: 10px; margin-bottom: 20px;'>
        <h1 style="color:white; font-size: 3em; margin-bottom: 10px;">
            📋 Dashboard Manuales
        </h1>
               
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Ruta de la carpeta de manuales relativa al directorio actual del script
manuales_dir = current_dir / 'manuales'

# --- Funciones de Utilidad ---

def load_markdown_files(folder_path: Path) -> Dict[str, str]:
    """
    Carga todos los archivos .md de una carpeta específica.

    Args:
        folder_path (Path): La ruta del directorio donde buscar los archivos Markdown.

    Returns:
        Dict[str, str]: Un diccionario donde las claves son los nombres de los archivos
                        (ej. 'mi_manual.md') y los valores son el contenido del archivo.
    """
    markdown_files = {}
    if folder_path.exists():
        for file_path in folder_path.glob('*.md'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    markdown_files[file_path.name] = content
            except Exception as e:
                st.error(f"Error al leer {file_path.name}: {e}")
    return markdown_files

def generate_toc(markdown_text: str) -> List[Tuple[str, str, str]]:
    """
    Genera una Tabla de Contenidos (TOC) a partir del texto Markdown.

    Extrae todos los encabezados (h1 a h6) y crea una lista de tuplas,
    donde cada tupla contiene (nivel_de_encabezado, texto_del_encabezado, ancla_generada).

    Args:
        markdown_text (str): El contenido completo de un archivo Markdown.

    Returns:
        List[Tuple[str, str, str]]: Una lista de tuplas con la información de cada encabezado.
    """
    headers = re.findall(r'^(#{1,6})\s(.*)', markdown_text, re.MULTILINE)
    toc = []
    for level, text in headers:
        # Limpiar el texto del título para crear una ancla amigable para URL
        # Elimina caracteres no alfanuméricos, espacios y guiones múltiples.
        clean_text = re.sub(r'[^\w\s-]', '', text).strip()
        anchor = clean_text.lower().replace(' ', '-').replace('--', '-')
        
        # Asegurar que el anchor no esté vacío (ej. si el título era solo caracteres especiales)
        if not anchor:
            anchor = f"header-{len(toc)}" # Genera un ancla única si el título no produce una válida.
        toc.append((level, text, anchor))
    return toc

def create_toc_component(headers: List[Tuple[int, str, str]]) -> str:
    if not headers:
        return "<div class='toc-scroll-container'>No hay encabezados para mostrar.</div>"
    
    list_items = [] # Usaremos una lista para construir los elementos
    for level, title, anchor in headers:
        # Aquí, aplanamos la cadena y eliminamos saltos de línea internos
        item_html = (
            f"<li style='margin-left: {(level-1)*15}px;'>"
            f"<a href='#{anchor}' "
            f"onclick='event.preventDefault(); document.getElementById(\"{anchor}\").scrollIntoView({{behavior:\"smooth\", block:\"start\"}});' "
            f"class='mkdocs-toc-link mkdocs-toc-link-level-{level}'>"
            f"{title}"
            f"</a>"
            f"</li>"
        )
        list_items.append(item_html.replace('\n', '')) # Eliminar saltos de línea dentro del item

    # Unir todos los elementos de la lista y luego envolverlos
    final_toc_html = (
        f"<div class='toc-scroll-container'>"
        f"<ul class='mkdocs-toc-list'>"
        f"{''.join(list_items)}" # Unir sin saltos de línea adicionales entre <li>
        f"</ul>"
        f"</div>"
    )
    return final_toc_html

def add_anchors_to_markdown(markdown_content: str, toc: List[Tuple[str, str, str]]) -> str:
    """
    Añade etiquetas de ancla HTML (`<a id="ancla"></a>`) a los encabezados del contenido Markdown.

    Esto es crucial para que los enlaces de la Tabla de Contenidos puedan navegar
    a secciones específicas del texto Markdown renderizado por Streamlit.

    Args:
        markdown_content (str): El contenido Markdown original.
        toc (List[Tuple[str, str, str]]): La Tabla de Contenidos generada previamente,
                                           que contiene los niveles, textos y anclas.

    Returns:
        str: El contenido Markdown con las etiquetas de ancla insertadas.
    """
    lines = markdown_content.split('\n')
    result_lines = []
    
    for line in lines:
        header_match = re.match(r'^(#{1,6})\s+(.+)', line)
        if header_match:
            level = header_match.group(1)
            title = header_match.group(2).strip() # .strip() para limpiar espacios extra
            
            # Buscar el anchor correspondiente en el TOC
            # Se busca por título y nivel de encabezado para mayor precisión
            anchor = next((a for l, t, a in toc if t.strip() == title and len(l) == len(level)), None)
            
            if anchor:
                # Inserta la ancla HTML antes del encabezado Markdown.
                # Streamlit renderizará la ancla como parte del HTML.
                result_lines.append(f'<a id="{anchor}"></a>')
                result_lines.append(line) # Mantener la línea original del encabezado
            else:
                result_lines.append(line)
        else:
            result_lines.append(line)
    
    return '\n'.join(result_lines)



# --- Función Principal de la Aplicación ---
def main():
    """
    Función principal que orquesta la aplicación Streamlit.

    - Carga los archivos Markdown.
    - Inyecta CSS personalizado para un look and feel similar a MkDocs.
    - Maneja la selección del manual.
    - Organiza el diseño en tres columnas:
        - Columna izquierda: Selector de manuales (simulando un sidebar de navegación).
        - Columna central: Contenido del manual seleccionado con anclas.
        - Columna derecha: Tabla de Contenidos interactiva del manual.
    """
    # --- CSS Personalizado para un look and feel similar a MkDocs Material ---
    # Esto se inyecta en el DOM de la página de Streamlit.
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Roboto+Mono:wght@400;500&display=swap');

        :root {
            --mkdocs-primary: #f7931e; /* Naranja fuerte */
            --mkdocs-primary-light: #ffb14e; /* Naranja más claro */
            --mkdocs-secondary: #0a738c; /* Azul/verde oscuro para acentos */
            --mkdocs-text-color: #333; /* Texto principal */
            --mkdocs-background-color: #f7f9fa; /* Fondo claro general */
            --mkdocs-card-background: #ffffff; /* Fondo para tarjetas/paneles */
            --mkdocs-border-color: #e0e0e0; /* Color de borde suave */
            --mkdocs-code-background: #eeeeee; /* Fondo para bloques de código */
            --mkdocs-code-text: #333; /* Texto para bloques de código */
        }

        body {
            font-family: 'Roboto', sans-serif;
            color: var(--mkdocs-text-color);
            background-color: var(--mkdocs-background-color);
        }

        /* Estilo para los headers de Streamlit */
        h1, h2, h3, h4, h5, h6 {
            color: var(--mkdocs-text-color);
            font-weight: 500;
        }

        /* Estilo para el contenedor principal de Streamlit */
        .stApp {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }

        /* Contenedores de columna para darles un aspecto de "card" */
        /* Nota: Estos selectores son específicos de la estructura DOM de Streamlit y pueden cambiar en futuras versiones. */
        /* Si el estilo se rompe, inspecciona el HTML de tu app Streamlit para encontrar los selectores correctos. */
        .st-emotion-cache-1jm6glt, .st-emotion-cache-nahz7x, .st-emotion-cache-nahz7x > div:first-child { 
            background-color: var(--mkdocs-card-background);
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid var(--mkdocs-border-color);
            height: fit-content; /* Asegura que la altura se ajuste al contenido */
        }
        
        /* Ajuste específico para la columna del contenido principal para que no tenga margin-bottom excesivo */
        .st-emotion-cache-nahz7x:nth-child(2) { /* Asumiendo que es la segunda columna */
            margin-bottom: 0; 
            padding-bottom: 0;
        }


        /* Ajustes específicos para la columna del selector (izquierda) */
        .st-emotion-cache-1jm6glt:first-child { /* Asumiendo que es la primera columna */
            padding-top: 15px; /* Ajustar padding superior */
        }

        /* Estilo para el selectbox (selector de manuales) */
        .st-emotion-cache-cnjvnn { /* Contenedor del selectbox */
            border-radius: 6px;
            border: 1px solid var(--mkdocs-border-color);
            background-color: var(--mkdocs-card-background);
        }
        .st-emotion-cache-1ckc33j { /* El selectbox en sí */
            background-color: var(--mkdocs-card-background);
            color: var(--mkdocs-text-color);
        }
        .st-emotion-cache-1dp5gkj { /* Icono de la flecha del selectbox */
            color: var(--mkdocs-primary);
        }

        /* Contenedor para la TOC con scroll */
        .toc-scroll-container {
            max-height: 600px; /* Ajusta la altura máxima según sea necesario */
            overflow-y: auto; /* Habilita el scroll vertical */
            padding-right: 10px; /* Espacio para que el scrollbar no se pegue al texto */
        }
        .toc-scroll-container::-webkit-scrollbar {
            width: 8px;
        }
        .toc-scroll-container::-webkit-scrollbar-thumb {
            background-color: var(--mkdocs-border-color);
            border-radius: 4px;
        }
        .toc-scroll-container::-webkit-scrollbar-track {
            background: transparent;
        }


        /* Estilo para los enlaces de la Tabla de Contenidos */
        .mkdocs-toc-list {
            list-style-type: none;
            padding-left: 0;
            margin-top: 10px;
        }

        .mkdocs-toc-list li {
            margin-bottom: 3px;
        }

        .mkdocs-toc-link {
            text-decoration: none;
            color: var(--mkdocs-text-color);
            display: block;
            padding: 4px 0;
            transition: all 0.2s ease-in-out;
            font-size: 0.9em;
        }
        .mkdocs-toc-link:hover {
            color: var(--mkdocs-primary);
            transform: translateX(3px); /* Pequeño efecto al pasar el ratón */
        }
        /* Ajuste de tamaño para los enlaces de TOC según el nivel */
        .mkdocs-toc-link-level-1 { font-weight: 500; font-size: 1em; }
        .mkdocs-toc-link-level-2 { font-weight: 400; font-size: 0.95em; }
        .mkdocs-toc-link-level-3 { font-weight: 300; font-size: 0.9em; }
        /* Y así sucesivamente para niveles 4, 5, 6 */


        /* Estilo para los bloques de código (Markdown) */
        pre code {
            font-family: 'Roboto Mono', monospace;
            background-color: var(--mkdocs-code-background) !important;
            color: var(--mkdocs-code-text) !important;
            border-radius: 5px;
            padding: 1em;
            overflow-x: auto; /* Para scroll horizontal en código largo */
        }

        /* Estilo para citas (blockquote) */
        blockquote {
            border-left: 4px solid var(--mkdocs-primary);
            padding-left: 15px;
            margin: 1em 0;
            color: var(--mkdocs-secondary);
            font-style: italic;
        }

        /* Estilo para enlaces normales dentro del contenido */
        a {
            color: var(--mkdocs-primary);
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }

        /* Otros elementos de Markdown pueden requerir más CSS */
        /* Por ejemplo, para tablas, listas, imágenes, etc. */
        </style>
        """,
        unsafe_allow_html=True
    )

    
    # Cargar archivos markdown de la carpeta 'manuales'
    markdown_files = load_markdown_files(manuales_dir)

    if not markdown_files:
        st.warning(f"⚠️ No se encontraron archivos .md en la carpeta: `{manuales_dir}`")
        st.info("💡 Añade archivos .md a la carpeta 'manuales' para comenzar.")
        return

    # Inicializar estado de sesión para el archivo seleccionado
    # Si no hay un manual seleccionado, toma el primero de la lista.
    if 'selected_manual' not in st.session_state:
        st.session_state.selected_manual = list(markdown_files.keys())[0]
    # Asegurarse de que el manual seleccionado aún exista (ej. si se eliminó un archivo)
    elif st.session_state.selected_manual not in markdown_files:
        st.session_state.selected_manual = list(markdown_files.keys())[0]


    # --- Sidebar - Selector de manuales ---
    with st.sidebar:
        st.markdown("---")
        st.markdown("#### 📚 Seleccionar Manual")
        file_options = list(markdown_files.keys())
        # Crea nombres más legibles para mostrar en el selectbox
        display_options = [f.replace('.md', '').replace('_', ' ').replace('-', ' ').title() for f in file_options]

        # Busca el índice del manual actualmente seleccionado para establecerlo como valor inicial
        try:
            selected_index = file_options.index(st.session_state.selected_manual)
        except ValueError:
            selected_index = 0 # Si por alguna razón el manual no se encuentra, selecciona el primero.

        # Selectbox para elegir manual
        selected_file = st.selectbox(
            "Manuales disponibles:",
            options=range(len(file_options)),
            format_func=lambda x: display_options[x], # Muestra los nombres limpios
            index=selected_index,
            key="manual_selector",
            label_visibility="collapsed" # Oculta la etiqueta predeterminada del selectbox
        )
        # Actualiza el estado de sesión con el archivo seleccionado
        st.session_state.selected_manual = file_options[selected_file]

    # --- Columna central y derecha - Contenido del manual y Tabla de Contenidos ---
    col_center, col_right = st.columns([9, 3], gap='medium')

    # --- Columna central - Contenido del manual ---
    with col_center:
        current_markdown_content = markdown_files.get(st.session_state.selected_manual, "")
        if current_markdown_content:
            # Genera la TOC para obtener las anclas
            toc_data = generate_toc(current_markdown_content)
            # Añade las anclas al contenido Markdown
            processed_content = add_anchors_to_markdown(current_markdown_content, toc_data)

            # Muestra el contenido Markdown. ¡unsafe_allow_html=True es CRUCIAL!
            # Permite a Streamlit renderizar las etiquetas HTML que hemos insertado.
            st.markdown(processed_content, unsafe_allow_html=True)
        else:
            st.info("Selecciona un manual de la izquierda para ver su contenido.")

    # --- Columna derecha - Tabla de Contenidos (TOC) ---
    with col_right:
        st.markdown("#### 📋 Tabla de contenidos")

        current_markdown_content = markdown_files.get(st.session_state.selected_manual, "")
        if current_markdown_content:
            toc_for_display = generate_toc(current_markdown_content)
            headers_for_toc_component = [(len(level), text, anchor) for level, text, anchor in toc_for_display]

            # Obtén la cadena HTML completa de la TOC
            generated_toc_html = create_toc_component(headers_for_toc_component)

            # Renderiza el componente de la TOC
            st.markdown(
                generated_toc_html, # Usamos la cadena generada directamente
                unsafe_allow_html=True
            )
        else:
            st.info("No hay contenido para generar el índice.")

# Punto de entrada de la aplicación
if __name__ == "__main__":
    main()