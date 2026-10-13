# Clasificador de signos del zodiaco dibujados a mano

Práctica Calificada 2 de Computación Gráfica. Partimos de la app de clase que
recolecta dibujos de las letras U, N e I
([PeterTXS09/letras_uni](https://github.com/PeterTXS09/letras_uni)), y la
adaptamos para reconocer los símbolos de los 6 primeros signos del zodiaco
dibujados a mano alzada:

| Clase | Símbolo | Carpeta |
|---|---|---|
| Aries | ♈ | `data/aries/` |
| Tauro | ♉ | `data/tauro/` |
| Géminis | ♊ | `data/geminis/` |
| Cáncer | ♋ | `data/cancer/` |
| Leo | ♌ | `data/leo/` |
| Virgo | ♍ | `data/virgo/` |

Meta: 500 dibujos por clase (3000 en total).

## Integrantes

- Andres 
- Montalvo 
- Jose
- Andrew

## Cómo correr la app en tu computadora

```bash
pip install -r requirements.txt
python main.py
```





## Rutas de la app

| Ruta | Para qué sirve |
|---|---|
| `/` | Página para dibujar |
| `/descargar` | Descarga todos los dibujos en `zodiaco_dibujos.zip` |
| `/prepare` | Arma `X.npy` (n, 200, 200) e `y.npy` (n,) igual que la app original |
| `/X.npy`, `/y.npy` | Descarga esos archivos después de entrar a `/prepare` |

## Despliegue en Railway

1. En Railway: New Project → Deploy from GitHub repo → este repositorio.
2. Agregar un Volume al servicio (por ejemplo montado en `/data`). Railway
   define `RAILWAY_VOLUME_MOUNT_PATH` y la app guarda ahí los dibujos, así no
   se pierden cuando la app se reinicia.
3. Settings → Networking → Generate Domain para tener el link público.

Sin Volume la app funciona igual, pero los dibujos se borran en cada
reinicio. En ese caso hay que descargar el `.zip` seguido.
