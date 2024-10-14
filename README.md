# DTorrent

A client and a distributed tracker service of BitTorrent

## Authors

- [Jesus Aldair Alfonso Perez](https://www.github.com/aldairlfp)
- [Mauro Bolado Vizoso](https://github.com/Mauro-Bolado)

## Descripción

### Objetivo

Como objetivo de este trabajo se tiene crear un conjunto formado por cliente - servidor que tenga una funcionalidad similar al protocolo Torrent.

#### Objetivos del servidor

- Tolerancia a fallos 2
- Replicación de los datos

#### Objetivos del cliente

- Descargas de multiples fuentes
- Debe ser una aplicación visual para facilitar el uso de la misma

### Tracker

Para la implementación del servidor de rastreo (Tracker Server) se utilizó un sitema distribuido. Dicha implementación usa un anillo de CHORD, que es una variación de las DHT(Distributed Hash Table). Nuestra implementación posee varias características específicas del problema.

Para cumplir con los objetivos, cada servidor comparte sus datos con su sucesor y a su vez con el sucesor del sucesor (posiciones 0 y 1 respectivamente en la "finger table"). Esto permite que al perder 2 servidores se garantiza que siempre exista al menos 1 con los datos en la red de CHORD, por consiguiente cumple el ambos objetivos encomendados.

### Cliente

La apliación cliente es un ejecutable (.exe) creado con PyQt5, que tiene presenta una interfaz visual con lo necesario para usar el cliente.

#### Forma de uso

- Abrir el ejecutable, o ejecutar con un intérprete de python el archivo ui_client.py.
- Si no está prestablecido es necesario seleccionar el fichero que se desea subir. Cuando se seleccione el archivo directamente el cliente hará de semilla de ese archivo y creará el .torrent para que el resto de los peer lo puedan descargar.
- Para iniciar la descarga es necesario contar con el archivo .torrent correspondiente a lo que deseamos descargar y seleccionarlo en el ordenador. Al hacer esto directamente inicia la descarga. 

#### Características del cliente

- El cliente hace una selección de peers con el fichero disponibles y comienza a descargar de todos hasta un máximo de 4 a la vez, para no sobrecargar la red.
- Para cada descarga se establece un hilo de ejecución (Thread) con el objetivo de poder realizar dscargas multiples, poder descargar varios archivos simultaneamente.

