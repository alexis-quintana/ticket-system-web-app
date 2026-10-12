---Por si ya tenian la BD , esto es para actualizar con mis datos
UPDATE empresas
SET nombre = 'AGROCASAGRANDE S.A.C.',
    ruc = '20601226015',
    sector = 'Agroindustria',
    num_trabajadores = 7886,
    contacto_nombre = 'Christian Llontop Flores',
    contacto_cargo = 'Jefe de T.I.',
    contacto_email = 'christian.llontop@agrofutura.com.pe'
WHERE nombre = 'Empresa en coordinación (demo)';