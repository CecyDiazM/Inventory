import sqlite3
import streamlit as st

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Control de Inventario - Tienda de Ropa",
    page_icon="🛍️",
    layout="wide",
)


# ==========================================
# GESTIÓN DE LA BASE DE DATOS (SQLite)
# ==========================================
def conectar_db():
    conn = sqlite3.connect("inventario_ropa.db")
    return conn


def crear_tabla():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            talla TEXT NOT NULL,
            precio REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()


# Inicializar la base de datos al arrancar
crear_tabla()

# ==========================================
# VISTA PRINCIPAL / INTERFAZ DE USUARIO
# ==========================================
st.title("🛍️ Sistema de Inventario - Boutique")
st.subheader("Gestiona tus prendas de forma rápida y ordenada")
st.markdown("---")

# --- SECCIÓN 1: PANEL DE MÉTRICAS (DASHBOARD) ---
conn = conectar_db()
cursor = conn.cursor()

# Consultas rápidas para el negocio
cursor.execute("SELECT SUM(stock) FROM productos")
total_prendas = cursor.fetchone()[0] or 0

cursor.execute("SELECT COUNT(*) FROM productos WHERE stock <= 3")
bajo_stock = cursor.fetchone()[0] or 0

cursor.execute("SELECT SUM(precio * stock) FROM productos")
valor_inventario = cursor.fetchone()[0] or 0.0

# Renderizar métricas en columnas
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.metric(label="Total de Prendas en Stock", value=f"{total_prendas} uds")
with col_m2:
    # Si hay productos en stock crítico, se muestra en rojo/alerta de forma nativa
    st.metric(
        label="Productos en Stock Crítico (≤ 3)",
        value=bajo_stock,
        delta="- Alerta" if bajo_stock > 0 else None,
        delta_color="inverse",
    )
with col_m3:
    st.metric(label="Valor Total del Inventario", value=f"${valor_inventario:,.2f}")

st.markdown("---")

# --- SECCIÓN 2: FORMULARIO PARA AÑADIR PRENDAS ---
# Usamos st.expander para que no ocupe espacio visual si no se está usando
with st.expander("➕ Registrar Nueva Prenda"):
    # Agrupamos en un formulario para evitar que Streamlit recargue la página con cada letra escrita
    with st.form("formulario_producto", clear_on_submit=True):
        col_f1, col_f2, col_f3 = st.columns(3)

        with col_f1:
            nombre = st.text_input("Nombre de la prenda", placeholder="Ej: Polera Oversize")
            categoria = st.selectbox(
                "Categoría", ["Poleras", "Pantalones", "Vestidos", "Chaquetas", "Accesorios"]
            )

        with col_f2:
            talla = st.selectbox("Talla", ["XS", "S", "M", "L", "XL", "Única"])
            precio = st.number_input("Precio de Venta ($)", min_value=0.0, step=1.0)

        with col_f3:
            stock = st.number_input(
                "Cantidad Inicial en Stock", min_value=0, step=1, value=10
            )

        # Botón de envío del formulario
        guardar = st.form_submit_button("Guardar Producto")

        if guardar:
            if nombre.strip() == "":
                st.error("❌ El nombre de la prenda no puede estar vacío.")
            else:
                cursor.execute(
                    "INSERT INTO productos (nombre, categoria, talla, precio, stock) VALUES (?, ?, ?, ?, ?)",
                    (nombre, categoria, talla, precio, stock),
                )
                conn.commit()
                st.success(f"✅ ¡{nombre} ({talla}) añadido correctamente!")
                st.rerun()  # Recarga la app para actualizar las tablas y métricas

# --- SECCIÓN 3: TABLA DE INVENTARIO INTERACTIVA ---
st.subheader("📦 Catálogo Actual e Inventario")

# Cargar los datos actuales para mostrarlos
import pandas as pd

df_productos = pd.read_sql_query("SELECT * FROM productos", conn)
conn.close()

if df_productos.empty:
    st.info("El inventario está vacío. ¡Añade tu primer producto arriba!")
else:
    # Buscador y Filtros rápidos
    col_b1, col_b2 = st.columns([2, 1])
    with col_b1:
        buscar = st.text_input("🔍 Buscar por nombre de prenda...").lower()
    with col_b2:
        filtro_talla = st.selectbox("Filtrar por Talla", ["Todas"] + list(df_productos["talla"].unique()))

    # Aplicar filtros al DataFrame de Pandas
    if buscar:
        df_productos = df_productos[df_productos["nombre"].str.lower().str.contains(buscar)]
    if filtro_talla != "Todas":
        df_productos = df_productos[df_productos["talla"] == filtro_talla]

    # Mostrar la tabla de manera interactiva. 
    # El data_editor permite al usuario modificar el stock o precio haciendo doble clic.
    st.write("💡 *Puedes editar los datos directamente en la tabla (doble clic) si lo deseas:*")
    
    productos_editados = st.data_editor(
        df_productos,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True), # El ID no se puede editar
            "nombre": "Prenda",
            "categoria": "Categoría",
            "talla": "Talla",
            "precio": st.column_config.NumberColumn("Precio", format="$%.2f"),
            "stock": st.column_config.NumberColumn("Stock Actual"),
        },
        disabled=["id"],
        hide_index=True,
        use_container_width=True
    )

    # Botón para guardar cambios si el usuario editó la tabla directamente
    if st.button("💾 Guardar Cambios de la Tabla"):
        conn = conectar_db()
        cursor = conn.cursor()
        for _, fila in productos_editados.iterrows():
            cursor.execute(
                "UPDATE productos SET nombre=?, categoria=?, talla=?, precio=?, stock=? WHERE id=?",
                (fila['nombre'], fila['categoria'], fila['talla'], fila['precio'], fila['stock'], fila['id'])
            )
        conn.commit()
        conn.close()
        st.success("¡Inventario actualizado con éxito!")
        st.rerun()
