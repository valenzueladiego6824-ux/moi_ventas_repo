from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.cache import cache_control
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Usuario
from .forms import LoginForm, RegistrarOrdenForm
import re

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def login_view(request):
    if 'usuario_id' in request.session:
        return redirect('inicio')
        
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            nombre_usuario = form.cleaned_data['nombre_usuario']
            password = form.cleaned_data['password']

            try:
                usuario = Usuario.objects.get(nombre_usuario=nombre_usuario)
                
                if usuario.check_password(password):
                    request.session['usuario_id'] = usuario.id_usuario
                    request.session['usuario_nombre'] = usuario.nombre_usuario
                    request.session['usuario_rol'] = usuario.rol
                    request.session.set_expiry(0)
                    
                    response = redirect('inicio')
                    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                    response['Pragma'] = 'no-cache'
                    response['Expires'] = 'Sat, 01 Jan 2000 00:00:00 GMT'
                    return response
                else:
                    messages.error(request, 'Usuario o contraseña incorrectos')
            except Usuario.DoesNotExist:
                messages.error(request, 'Usuario o contraseña incorrectos')
    else:
        form = LoginForm()
    
    response = render(request, 'login.html', {'form': form})
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = 'Sat, 01 Jan 2000 00:00:00 GMT'
    return response


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def logout_view(request):
    request.session.flush()
    
    response = redirect('login')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = 'Sat, 01 Jan 2000 00:00:00 GMT'
    response.delete_cookie('sessionid')
    response.delete_cookie('csrftoken')
    
    return response


def login_required_contenido(view_func):
    def wrapper(request, *args, **kwargs):
        if 'usuario_id' not in request.session:
            messages.error(request, 'Debe iniciar sesión para acceder a esta página.')
            return redirect('login')
        
        response = view_func(request, *args, **kwargs)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = 'Sat, 01 Jan 2000 00:00:00 GMT'
        return response
    return wrapper


@login_required_contenido
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def inicio(request):
    return render(request, 'inicio.html')


@login_required_contenido
def api_consultar_datos(request):
    busqueda = request.GET.get('busqueda', '').strip()
    
    with connection.cursor() as cursor:
        query = """
            SELECT 
                oc.numero_orden, 
                oc.fecha, 
                oc.estatus, 
                oc.solicitante, 
                o.obra as obra,
                oc.metodo_pago,
                f.folio_factura, 
                f.subtotal, 
                f.iva, 
                f.total 
            FROM orden_compra oc
            JOIN obra o ON oc.id_obra = o.id_obra
            JOIN facturas f ON oc.numero_orden = f.numero_orden 
            WHERE 1=1
        """
        parametros = []
        
        if busqueda:
            query += """
                AND (
                    oc.numero_orden::TEXT ILIKE %s OR
                    oc.solicitante ILIKE %s OR 
                    o.obra ILIKE %s OR
                    f.folio_factura ILIKE %s OR
                    oc.estatus ILIKE %s
                )
            """
            parametros = [f'%{busqueda}%'] * 5
        
        # Ordenar por fecha descendente (más recientes primero)
        query += " ORDER BY oc.fecha DESC LIMIT 200"
        
        cursor.execute(query, parametros)
        resultados = cursor.fetchall()
    
    datos = []
    for row in resultados:
        datos.append({
            'numero_orden': row[0],
            'fecha': row[1].strftime('%Y-%m-%d') if row[1] else None,
            'estatus': row[2],
            'solicitante': row[3],
            'obra': row[4],
            'metodo_pago': row[5],
            'folio_factura': row[6],
            'subtotal': float(row[7]) if row[7] else 0,
            'iva': float(row[8]) if row[8] else 0,
            'total': float(row[9]) if row[9] else 0,
        })
    
    return JsonResponse(datos, safe=False)


@login_required_contenido
def api_detalles_orden(request, numero_orden):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    oc.numero_orden, oc.fecha, oc.estatus, oc.solicitante, 
                    o.obra as obra,
                    oc.metodo_pago,
                    f.folio_factura, f.fecha_emision, f.subtotal, f.iva, f.total 
                FROM orden_compra oc
                JOIN obra o ON oc.id_obra = o.id_obra
                JOIN facturas f ON oc.numero_orden = f.numero_orden 
                WHERE oc.numero_orden = %s
            """, [numero_orden])
            
            orden_data = cursor.fetchone()
            
            if not orden_data:
                return JsonResponse({'error': 'Orden no encontrada'}, status=404)
            
            cursor.execute("""
                SELECT 
                    a.nombre_articulo, a.unidad, af.cantidad, af.precio_unitario 
                FROM articulos a, articulos_factura af 
                WHERE a.id_articulo = af.id_articulo 
                    AND af.numero_orden = %s
                ORDER BY a.nombre_articulo
            """, [numero_orden])
            
            articulos = cursor.fetchall()
        
        articulos_lista = []
        for art in articulos:
            articulos_lista.append({
                'nombre_articulo': art[0],
                'unidad': art[1],
                'cantidad': float(art[2]) if art[2] else 0,
                'precio_unitario': float(art[3]) if art[3] else 0,
            })
        
        respuesta = {
            'numero_orden': orden_data[0],
            'fecha': orden_data[1].strftime('%Y-%m-%d') if orden_data[1] else None,
            'estatus': orden_data[2],
            'solicitante': orden_data[3],
            'obra': orden_data[4],
            'metodo_pago': orden_data[5],
            'folio_factura': orden_data[6],
            'fecha_emision': orden_data[7].strftime('%Y-%m-%d') if orden_data[7] else None,
            'subtotal': float(orden_data[8]) if orden_data[8] else 0,
            'iva': float(orden_data[9]) if orden_data[9] else 0,
            'total': float(orden_data[10]) if orden_data[10] else 0,
            'articulos': articulos_lista
        }
        
        return JsonResponse(respuesta)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@login_required_contenido
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def registrar_articulos(request):
    from django.db import transaction
    
    if request.method == 'POST':
        form = RegistrarOrdenForm(request.POST)
        
        if form.is_valid():
            numero_orden = form.cleaned_data['numero_orden']
            fecha_orden = form.cleaned_data['fecha']
            obra_input = form.cleaned_data['obra_input']
            solicitante_input = form.cleaned_data['solicitante_input']
            estatus_input = form.cleaned_data['estatus_input']
            metodo_pago = form.cleaned_data['metodo_pago']
            usuario_id = request.session.get('usuario_id')

            folio_factura = request.POST.get('folio_factura', '').strip()
            fecha_factura = request.POST.get('fecha_factura', '').strip()
            proveedor_nombre = request.POST.get('proveedor', '').strip()
            subtotal = request.POST.get('subtotal', '0')
            iva = request.POST.get('iva', '0')
            total = request.POST.get('total', '0')

            if not folio_factura:
                messages.error(request, 'El folio de factura es obligatorio')
                return render(request, 'registrar_articulos.html', {'form': form})
            
            if not proveedor_nombre:
                messages.error(request, 'El proveedor es obligatorio')
                return render(request, 'registrar_articulos.html', {'form': form})

            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        # Buscar obra existente
                        cursor.execute("""
                            SELECT id_obra FROM obra 
                            WHERE obra = %s OR codigo_obra = %s
                        """, [obra_input, obra_input])
                        
                        obra_result = cursor.fetchone()
                        if obra_result:
                            id_obra = obra_result[0]
                        else:
                            cursor.execute("""
                                INSERT INTO obra (obra, codigo_obra) 
                                VALUES (%s, %s)
                                RETURNING id_obra
                            """, [obra_input, obra_input])
                            id_obra = cursor.fetchone()[0]

                        # Insertar orden_compra
                        cursor.execute("""
                            INSERT INTO orden_compra 
                            (numero_orden, fecha, estatus, solicitante, id_usuario, id_obra, metodo_pago)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, [numero_orden, fecha_orden, estatus_input, solicitante_input, usuario_id, id_obra, metodo_pago])

                        # Buscar o insertar proveedor
                        cursor.execute("""
                            SELECT id_proveedor FROM proveedores 
                            WHERE nombre_proveedor = %s
                        """, [proveedor_nombre])
                        
                        proveedor_result = cursor.fetchone()
                        if proveedor_result:
                            id_proveedor = proveedor_result[0]
                        else:
                            cursor.execute("""
                                INSERT INTO proveedores (nombre_proveedor) 
                                VALUES (%s)
                                RETURNING id_proveedor
                            """, [proveedor_nombre])
                            id_proveedor = cursor.fetchone()[0]

                        # Insertar factura
                        cursor.execute("""
                            INSERT INTO facturas 
                            (folio_factura, numero_orden, fecha_emision, subtotal, iva, total) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                            RETURNING folio_factura
                        """, [folio_factura, numero_orden, fecha_factura, subtotal, iva, total])

                        # ===========================================
                        # SECCIÓN DE ARTÍCULOS - VERSIÓN ORIGINAL
                        # ===========================================
                        articulos_data = {}
                        for key, value in request.POST.items():
                            match = re.match(r'articulos\[(\d+)\]\[(\w+)\]', key)
                            if match:
                                idx = match.group(1)
                                campo = match.group(2)
                                
                                if idx not in articulos_data:
                                    articulos_data[idx] = {}
                                articulos_data[idx][campo] = value

                        if not articulos_data:
                            raise Exception("Debe agregar al menos un artículo")

                        for idx, articulo in articulos_data.items():
                            descripcion = articulo.get('descripcion', '').strip()
                            unidad = articulo.get('unidad', '').strip()
                            clave = articulo.get('clave', '').strip()
                            cantidad = articulo.get('cantidad', '0')
                            precio = articulo.get('precio', '0')
                            
                            if not descripcion or not unidad:
                                raise Exception(f"Artículo {idx}: Descripción y unidad obligatorias")
                            
                            # Buscar artículo existente por nombre y proveedor (como originalmente)
                            if clave:
                                cursor.execute("""
                                    SELECT id_articulo FROM articulos 
                                    WHERE clave_articulo = %s AND id_proveedor = %s
                                """, [clave, id_proveedor])
                            else:
                                cursor.execute("""
                                    SELECT id_articulo FROM articulos 
                                    WHERE nombre_articulo = %s AND id_proveedor = %s
                                """, [descripcion, id_proveedor])
                            
                            articulo_result = cursor.fetchone()
                            
                            if articulo_result:
                                id_articulo = articulo_result[0]
                            else:
                                cursor.execute("""
                                    INSERT INTO articulos 
                                    (nombre_articulo, unidad, clave_articulo, id_proveedor) 
                                    VALUES (%s, %s, %s, %s)
                                    RETURNING id_articulo
                                """, [descripcion, unidad, clave, id_proveedor])
                                id_articulo = cursor.fetchone()[0]
                            
                            cursor.execute("""
                                INSERT INTO articulos_factura 
                                (folio_factura, numero_orden, id_articulo, cantidad, precio_unitario) 
                                VALUES (%s, %s, %s, %s, %s)
                            """, [folio_factura, numero_orden, id_articulo, cantidad, precio])
                        
                        # ===========================================
                        # FIN SECCIÓN DE ARTÍCULOS
                        # ===========================================
                    
                    messages.success(request, 'Orden de compra registrada correctamente')
                    return redirect('inicio')
                
            except Exception as e:
                messages.error(request, f'Error al registrar la orden: {str(e)}')
                import traceback
                traceback.print_exc()
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario')
    else:
        form = RegistrarOrdenForm()

    return render(request, 'registrar_articulos.html', {
        'titulo': 'Registrar Orden de Compra',
        'mensaje': 'Ingresa los datos de la orden de compra',
        'form': form
    })


@csrf_exempt
@login_required_contenido
def eliminar_orden(request, numero_orden):
    if request.method == 'DELETE':
        try:
            with connection.cursor() as cursor:
                # Con ON CASCADE, solo necesitas eliminar la orden_compra
                cursor.execute("DELETE FROM orden_compra WHERE numero_orden = %s", [numero_orden])
                return JsonResponse({'success': True, 'message': 'Orden eliminada correctamente'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@csrf_exempt
@login_required_contenido
def actualizar_orden(request, numero_orden):
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            
            with connection.cursor() as cursor:
                # Verificar existencia
                cursor.execute("SELECT folio_factura FROM facturas WHERE numero_orden = %s", [numero_orden])
                resultado = cursor.fetchone()
                if not resultado:
                    return JsonResponse({'success': False, 'error': 'Orden no encontrada'}, status=404)
                
                # Actualizar orden_compra incluyendo metodo_pago
                cursor.execute("""
                    UPDATE orden_compra 
                    SET fecha = %s, estatus = %s, solicitante = %s, metodo_pago = %s
                    WHERE numero_orden = %s
                """, [data['fecha'], data['estatus'], data['solicitante'], 
                      data['metodo_pago'], numero_orden])
                
                # Actualizar factura
                cursor.execute("""
                    UPDATE facturas 
                    SET fecha_emision = %s, subtotal = %s, iva = %s, total = %s
                    WHERE numero_orden = %s
                """, [data['fecha_emision'], data['subtotal'], 
                      data['iva'], data['total'], numero_orden])
                
                # Eliminar artículos existentes
                cursor.execute("DELETE FROM articulos_factura WHERE numero_orden = %s", [numero_orden])
                
                # Insertar nuevos artículos
                for art in data['articulos']:
                    cursor.execute("""
                        SELECT id_articulo FROM articulos 
                        WHERE nombre_articulo = %s
                    """, [art['nombre_articulo']])
                    
                    art_result = cursor.fetchone()
                    if art_result:
                        id_articulo = art_result[0]
                    else:
                        cursor.execute("""
                            INSERT INTO articulos (nombre_articulo, unidad) 
                            VALUES (%s, %s) RETURNING id_articulo
                        """, [art['nombre_articulo'], art['unidad']])
                        id_articulo = cursor.fetchone()[0]
                    
                    cursor.execute("""
                        INSERT INTO articulos_factura 
                        (folio_factura, numero_orden, id_articulo, cantidad, precio_unitario) 
                        VALUES (%s, %s, %s, %s, %s)
                    """, [data['folio_factura'], numero_orden, id_articulo, 
                          art['cantidad'], art['precio_unitario']])
            
            return JsonResponse({'success': True, 'message': 'Orden actualizada correctamente'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required_contenido
def api_obras(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT obra 
            FROM obra 
            ORDER BY obra
        """)
        obras = cursor.fetchall()
    
    datos = [row[0] for row in obras]
    return JsonResponse(datos, safe=False)


@login_required_contenido
def api_proveedores(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id_proveedor, nombre_proveedor FROM proveedores ORDER BY nombre_proveedor")
        proveedores = cursor.fetchall()
    
    datos = [{'id': row[0], 'nombre': row[1]} for row in proveedores]
    return JsonResponse(datos, safe=False)


@login_required_contenido
def api_estatus(request):
    estatus_options = ['PENDIENTE', 'CERRADA', 'CANCELADA']
    return JsonResponse(estatus_options, safe=False)


@login_required_contenido
def api_solicitantes(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT solicitante FROM orden_compra WHERE solicitante IS NOT NULL ORDER BY solicitante")
        solicitantes = cursor.fetchall()
    
    datos = [row[0] for row in solicitantes]
    return JsonResponse(datos, safe=False)


@login_required_contenido
def api_articulos(request):
    """Devuelve lista de artículos existentes"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT nombre_articulo 
            FROM articulos 
            WHERE nombre_articulo IS NOT NULL AND nombre_articulo != ''
            ORDER BY nombre_articulo
            LIMIT 500
        """)
        resultados = cursor.fetchall()
    
    datos = [row[0] for row in resultados]
    return JsonResponse(datos, safe=False)

@login_required_contenido
def api_unidades(request):
    """Devuelve lista de unidades existentes"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT unidad 
            FROM articulos 
            WHERE unidad IS NOT NULL AND unidad != ''
            ORDER BY unidad
        """)
        resultados = cursor.fetchall()
    
    datos = [row[0] for row in resultados]
    return JsonResponse(datos, safe=False)


# ============================================
# REPORTES - VERSIÓN LIMPIA Y ORGANIZADA
# ============================================

@login_required_contenido
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def reportes(request):
    """Vista principal de reportes"""
    return render(request, 'reportes.html', {
        'titulo': 'Reportes',
        'mensaje': 'Módulo de reportes'
    })


@login_required_contenido
def api_reporte_busqueda(request):
    """Búsqueda por obra, período, artículo o proveedor - SIN canceladas"""
    obra = request.GET.get('obra', '').strip()
    mes = request.GET.get('mes', '')
    año = request.GET.get('anio', '')
    articulo = request.GET.get('articulo', '').strip()
    proveedor = request.GET.get('proveedor', '').strip()
    
    query = """
        SELECT 
            o.obra,
            oc.numero_orden,
            oc.fecha,
            a.nombre_articulo,
            a.unidad,
            af.cantidad,
            af.precio_unitario,
            p.nombre_proveedor
        FROM obra o
        JOIN orden_compra oc ON o.id_obra = oc.id_obra
        JOIN facturas f ON oc.numero_orden = f.numero_orden
        JOIN articulos_factura af ON f.folio_factura = af.folio_factura
        JOIN articulos a ON af.id_articulo = a.id_articulo
        JOIN proveedores p ON a.id_proveedor = p.id_proveedor
        WHERE oc.estatus != 'CANCELADA'  -- ← FILTRO
    """
    params = []
    
    if obra:
        query += " AND o.obra = %s"
        params.append(obra)
    if mes:
        query += " AND EXTRACT(MONTH FROM oc.fecha) = %s"
        params.append(mes)
    if año:
        query += " AND EXTRACT(YEAR FROM oc.fecha) = %s"
        params.append(año)
    if articulo:
        query += " AND a.nombre_articulo ILIKE %s"
        params.append(f'%{articulo}%')
    if proveedor:
        query += " AND p.nombre_proveedor ILIKE %s"
        params.append(f'%{proveedor}%')
    
    query += " ORDER BY oc.fecha DESC LIMIT 500"
    
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        resultados = cursor.fetchall()
    
    datos = []
    for row in resultados:
        datos.append({
            'obra': row[0],
            'orden': row[1],
            'fecha': row[2].strftime('%Y-%m-%d') if row[2] else None,
            'articulo': row[3],
            'unidad': row[4],
            'cantidad': float(row[5]) if row[5] else 0,
            'precio': float(row[6]) if row[6] else 0,
            'proveedor': row[7]
        })
    
    return JsonResponse(datos, safe=False)


@login_required_contenido
def reporte_compras_mensuales(request):
    """Compras mensuales - SIN canceladas"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                EXTRACT(YEAR FROM oc.fecha) AS anio,
                EXTRACT(MONTH FROM oc.fecha) AS mes,
                COUNT(DISTINCT oc.numero_orden) AS total_ordenes,
                SUM(f.total) AS gasto_total
            FROM orden_compra oc
            INNER JOIN facturas f ON f.numero_orden = oc.numero_orden
            WHERE oc.estatus != 'CANCELADA'  -- ← FILTRO
            GROUP BY anio, mes
            ORDER BY anio DESC, mes DESC
        """)
        resultados = cursor.fetchall()
    
    datos = []
    for row in resultados:
        datos.append({
            'anio': int(row[0]) if row[0] else 0,
            'mes': int(row[1]) if row[1] else 0,
            'ordenes': row[2],
            'total': float(row[3]) if row[3] else 0
        })
    
    return JsonResponse(datos, safe=False)


@login_required_contenido
def reporte_obra_resumen(request):
    """Resumen de gastos por obra - Solo órdenes activas"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                o.obra,
                COUNT(DISTINCT oc.numero_orden) AS total_ordenes,
                SUM(f.total) AS total_gastado
            FROM obra o
            INNER JOIN orden_compra oc ON o.id_obra = oc.id_obra
            INNER JOIN facturas f ON oc.numero_orden = f.numero_orden
            WHERE oc.estatus != 'CANCELADA'
            GROUP BY o.obra
            ORDER BY total_gastado DESC
        """)
        resultados = cursor.fetchall()
    
    datos = [{
        'obra': row[0],
        'ordenes': row[1],
        'total': float(row[2]) if row[2] else 0
    } for row in resultados]
    
    return JsonResponse(datos, safe=False)


@login_required_contenido
def reporte_obra_detalle(request):
    """Detalle de órdenes por obra - Solo órdenes activas"""
    obra = request.GET.get('obra', '').strip()
    
    if not obra:
        return JsonResponse([], safe=False)
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                o.obra,
                oc.numero_orden,
                oc.fecha,
                oc.estatus,
                f.folio_factura,
                f.total,
                COUNT(af.id_articulo) as total_articulos
            FROM obra o
            INNER JOIN orden_compra oc ON o.id_obra = oc.id_obra
            INNER JOIN facturas f ON oc.numero_orden = f.numero_orden
            INNER JOIN articulos_factura af ON f.folio_factura = af.folio_factura
            WHERE o.obra = %s AND oc.estatus != 'CANCELADA'
            GROUP BY o.obra, oc.numero_orden, oc.fecha, oc.estatus, f.folio_factura, f.total
            ORDER BY oc.fecha DESC
        """, [obra])
        resultados = cursor.fetchall()
    
    datos = [{
        'obra': row[0],
        'orden': row[1],
        'fecha': row[2].strftime('%Y-%m-%d') if row[2] else None,
        'estatus': row[3],
        'folio': row[4],
        'total': float(row[5]) if row[5] else 0,
        'articulos': row[6]
    } for row in resultados]
    
    return JsonResponse(datos, safe=False)


@csrf_exempt
@login_required_contenido
def exportar_reporte_excel(request):
    """Exporta cualquier reporte a Excel"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        import pandas as pd
        import json
        from django.http import HttpResponse
        import io
        import re
        
        data = json.loads(request.body)
        reporte_data = data.get('data', [])
        columnas = data.get('columnas', [])
        titulo = data.get('titulo', 'Reporte')
        
        # Limpiar el título para nombres de hoja de Excel
        sheet_name = re.sub(r'[\/:*?"<>|]', ' ', titulo)
        sheet_name = sheet_name[:31]
        
        if not reporte_data:
            return JsonResponse({'error': 'No hay datos para exportar'}, status=400)
        
        # Crear DataFrame
        df = pd.DataFrame(reporte_data)
        
        # Renombrar columnas si se especificaron
        if columnas and len(columnas) == len(df.columns):
            df.columns = columnas
        
        # Crear archivo Excel en memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Ajustar ancho de columnas
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Crear respuesta HTTP
        filename = re.sub(r'[\/:*?"<>|]', '_', titulo)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

# Usuarios    

def gerente_required(view_func):
    def wrapper(request, *args, **kwargs):
        if 'usuario_id' not in request.session:
            messages.error(request, 'Debe iniciar sesión')
            return redirect('login')
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT rol FROM usuarios WHERE id_usuario = %s", 
                         [request.session['usuario_id']])
            usuario = cursor.fetchone()
            if not usuario or usuario[0] != 'Gerente':
                messages.error(request, 'Acceso restringido a Gerentes')
                return redirect('inicio')
        
        return view_func(request, *args, **kwargs)
    return wrapper


@gerente_required
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def gestion_usuarios(request):
    """Vista principal de gestión de usuarios"""
    return render(request, 'gestion-usuarios.html', {
        'titulo': 'Gestión de Usuarios'
    })


@gerente_required
def api_usuarios(request):
    """Listar todos los usuarios"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                id_usuario,
                nombre,
                apellido,
                nombre_usuario,
                rol
            FROM usuarios
            ORDER BY nombre
        """)
        usuarios = cursor.fetchall()
    
    datos = []
    for row in usuarios:
        datos.append({
            'id': row[0],
            'nombre': row[1],
            'apellido': row[2] or '',
            'usuario': row[3],
            'rol': row[4] or 'Usuario'
        })
    
    return JsonResponse(datos, safe=False)


@gerente_required
def api_crear_usuario(request):
    """Crear nuevo usuario"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        
        nombre = data.get('nombre', '').strip()
        apellido = data.get('apellido', '').strip()
        nombre_usuario = data.get('usuario', '').strip()
        password = data.get('password', '')
        rol = data.get('rol', 'Usuario')
        
        # Validaciones básicas
        if not nombre or not nombre_usuario or not password:
            return JsonResponse({'success': False, 'error': 'Campos obligatorios faltantes'}, status=400)
        
        # Hashear contraseña
        password_hash = make_password(password)
        
        with connection.cursor() as cursor:
            # Verificar si usuario ya existe
            cursor.execute("SELECT id_usuario FROM usuarios WHERE nombre_usuario = %s", [nombre_usuario])
            if cursor.fetchone():
                return JsonResponse({'success': False, 'error': 'El nombre de usuario ya existe'}, status=400)
            
            # Insertar nuevo usuario
            cursor.execute("""
                INSERT INTO usuarios 
                (nombre, apellido, nombre_usuario, password_hash, rol)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id_usuario
            """, [nombre, apellido, nombre_usuario, password_hash, rol])
            
            nuevo_id = cursor.fetchone()[0]
        
        return JsonResponse({'success': True, 'id': nuevo_id, 'message': 'Usuario creado correctamente'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@gerente_required
def api_usuario_detalle(request, usuario_id):
    """Obtener detalles de un usuario"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id_usuario,
                    nombre,
                    apellido,
                    nombre_usuario,
                    rol
                FROM usuarios
                WHERE id_usuario = %s
            """, [usuario_id])
            
            usuario = cursor.fetchone()
            
            if not usuario:
                return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
            
            datos = {
                'id': usuario[0],
                'nombre': usuario[1],
                'apellido': usuario[2] or '',
                'usuario': usuario[3],
                'rol': usuario[4] or 'Usuario'
            }
            
            return JsonResponse(datos)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@gerente_required
def api_actualizar_usuario(request, usuario_id):
    """Actualizar usuario"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        
        nombre = data.get('nombre', '').strip()
        apellido = data.get('apellido', '').strip()
        nombre_usuario = data.get('usuario', '').strip()
        password = data.get('password', '')  # Opcional
        rol = data.get('rol', 'Usuario')
        
        if not nombre or not nombre_usuario:
            return JsonResponse({'success': False, 'error': 'Campos obligatorios faltantes'}, status=400)
        
        with connection.cursor() as cursor:
            # Verificar si el usuario existe
            cursor.execute("SELECT password_hash FROM usuarios WHERE id_usuario = %s", [usuario_id])
            resultado = cursor.fetchone()
            if not resultado:
                return JsonResponse({'success': False, 'error': 'Usuario no encontrado'}, status=404)
            
            # Verificar si nombre_usuario ya existe en otro usuario
            cursor.execute("SELECT id_usuario FROM usuarios WHERE nombre_usuario = %s AND id_usuario != %s", 
                         [nombre_usuario, usuario_id])
            if cursor.fetchone():
                return JsonResponse({'success': False, 'error': 'El nombre de usuario ya existe'}, status=400)
            
            # Actualizar contraseña solo si se proporcionó una nueva
            if password:
                password_hash = make_password(password)
                cursor.execute("""
                    UPDATE usuarios 
                    SET nombre = %s, apellido = %s, nombre_usuario = %s, 
                        password_hash = %s, rol = %s
                    WHERE id_usuario = %s
                """, [nombre, apellido, nombre_usuario, password_hash, rol, usuario_id])
            else:
                cursor.execute("""
                    UPDATE usuarios 
                    SET nombre = %s, apellido = %s, nombre_usuario = %s, rol = %s
                    WHERE id_usuario = %s
                """, [nombre, apellido, nombre_usuario, rol, usuario_id])
        
        return JsonResponse({'success': True, 'message': 'Usuario actualizado correctamente'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@gerente_required
def api_eliminar_usuario(request, usuario_id):
    """Eliminar usuario"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        # No permitir eliminar el propio usuario
        if usuario_id == request.session.get('usuario_id'):
            return JsonResponse({'success': False, 'error': 'No puedes eliminar tu propio usuario'}, status=400)
        
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM usuarios WHERE id_usuario = %s RETURNING id_usuario", [usuario_id])
            if not cursor.fetchone():
                return JsonResponse({'success': False, 'error': 'Usuario no encontrado'}, status=404)
        
        return JsonResponse({'success': True, 'message': 'Usuario eliminado correctamente'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)