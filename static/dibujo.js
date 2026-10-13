(function () {
  "use strict";

  const SIGNOS = window.ZODIACO.signos;
  const META = window.ZODIACO.meta;
  const CLASES = {};
  Object.keys(SIGNOS).forEach(function (k) { CLASES[k] = SIGNOS[k].nombre; });
  const GROSOR = 7;            // grosor del trazo en píxeles del lienzo (200x200)

  const datosSigno = document.getElementById("datos-signo");

  const lienzo = document.getElementById("lienzo");
  const ctx = lienzo.getContext("2d");
  const vacio = document.getElementById("lienzo-vacio");
  const nombreSigno = document.getElementById("nombre-signo");
  const inputAutor = document.getElementById("autor");
  const btnBorrar = document.getElementById("btn-borrar");
  const btnCambiar = document.getElementById("btn-cambiar");
  const btnGuardar = document.getElementById("btn-guardar");
  const aviso = document.getElementById("aviso");
  const avisoTexto = document.getElementById("aviso-texto");
  const btnDeshacer = document.getElementById("btn-deshacer");
  const total = document.getElementById("total");

  let claseActual = null;
  let dibujando = false;
  let ultimo = null;           
  let hayTrazo = false;
  let ultimoGuardado = null;   
  let ocupado = false;

  // ---------- nombre de quien dibuja 
  try { inputAutor.value = localStorage.getItem("zodiaco-autor") || ""; } catch (e) { /* sin almacenamiento */ }
  inputAutor.addEventListener("change", function () {
    try { localStorage.setItem("zodiaco-autor", inputAutor.value.trim()); } catch (e) { /* sin almacenamiento */ }
  });

  // ---------- dibujo
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  function punto(e) {
    const r = lienzo.getBoundingClientRect();
    return {
      x: (e.clientX - r.left) * (lienzo.width / r.width),
      y: (e.clientY - r.top) * (lienzo.height / r.height),
    };
  }

  function trazar(desde, hasta) {
    ctx.strokeStyle = getComputedStyle(document.body).getPropertyValue("--elemento").trim() || "#f6c453";
    ctx.lineWidth = GROSOR;
    ctx.beginPath();
    ctx.moveTo(desde.x, desde.y);
    ctx.lineTo(hasta.x, hasta.y);
    ctx.stroke();
    if (!hayTrazo) {
      hayTrazo = true;
      vacio.hidden = true;
    }
  }

  lienzo.addEventListener("pointerdown", function (e) {
    e.preventDefault();
    lienzo.setPointerCapture(e.pointerId);
    dibujando = true;
    ultimo = punto(e);
    trazar(ultimo, ultimo);   // un toque deja un punto
  });

  lienzo.addEventListener("pointermove", function (e) {
    if (!dibujando) return;
    const eventos = e.getCoalescedEvents ? e.getCoalescedEvents() : [e];
    for (const ev of (eventos.length ? eventos : [e])) {
      const p = punto(ev);
      trazar(ultimo, p);
      ultimo = p;
    }
  });

  function terminar() { dibujando = false; ultimo = null; }
  lienzo.addEventListener("pointerup", terminar);
  lienzo.addEventListener("pointercancel", terminar);

  function borrar() {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, lienzo.width, lienzo.height);
    hayTrazo = false;
    vacio.hidden = false;
  }

  // ---------- signo pedido
  function mostrarSigno(clase) {
    const s = SIGNOS[clase];
    claseActual = clase;
    document.body.dataset.elemento = s.elemento;
    nombreSigno.textContent = s.nombre;
    datosSigno.innerHTML = "";
    const el = document.createElement("b");
    el.textContent = s.elemento.charAt(0).toUpperCase() + s.elemento.slice(1);
    datosSigno.append("Elemento ", el, ". Del " + s.fechas.replace(" - ", " al ") + ".");
    document.querySelectorAll(".glifo").forEach(function (g) {
      g.hidden = g.dataset.clase !== clase;
    });
    document.querySelectorAll(".signo").forEach(function (fila) {
      fila.classList.toggle("actual", fila.dataset.clase === clase);
    });
  }

  function mostrarConteo(conteo) {
    let suma = 0;
    Object.keys(conteo).forEach(function (clase) {
      const n = conteo[clase];
      suma += n;
      const fila = document.querySelector('.signo[data-clase="' + clase + '"]');
      if (!fila) return;
      fila.querySelector(".signo-cuenta b").textContent = n;
      fila.querySelector(".signo-relleno").style.width = Math.min(100, (n / META) * 100) + "%";
    });
    const metaTotal = META * Object.keys(CLASES).length;
    total.textContent = suma + " de " + metaTotal + " dibujos";
  }

  function avisar(texto, opciones) {
    opciones = opciones || {};
    avisoTexto.textContent = texto;
    aviso.classList.toggle("error", !!opciones.error);
    btnDeshacer.hidden = !opciones.deshacer;
    aviso.hidden = false;
  }

  async function pedir(url, cuerpo) {
    const resp = await fetch(url, cuerpo ? {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo),
    } : undefined);
    let datos = {};
    try { datos = await resp.json(); } catch (e) { /* respuesta sin JSON */ }
    if (!resp.ok) throw new Error(datos.error || "No se pudo conectar con el servidor. Intenta de nuevo.");
    return datos;
  }

  async function cargarEstado(evitar) {
    const url = "/api/estado" + (evitar ? "?evitar=" + encodeURIComponent(evitar) : "");
    const datos = await pedir(url);
    mostrarConteo(datos.conteo);
    return datos.siguiente;
  }

  // ---------- acciones
  async function guardar() {
    if (ocupado) return;
    if (!hayTrazo) {
      avisar("El recuadro está vacío. Dibuja el signo antes de guardar.", { error: true });
      return;
    }
    ocupado = true;
    btnGuardar.disabled = true;
    try {
      const datos = await pedir("/api/guardar", {
        clase: claseActual,
        imagen: lienzo.toDataURL("image/png"),
        autor: inputAutor.value,
      });
      ultimoGuardado = { clase: datos.clase, archivo: datos.archivo };
      mostrarConteo(datos.conteo);
      const n = datos.conteo[datos.clase];
      avisar("Guardado. " + CLASES[datos.clase] + " lleva " + n + (n === 1 ? " dibujo." : " dibujos."), { deshacer: true });
      borrar();
      mostrarSigno(datos.siguiente);
    } catch (err) {
      avisar(err.message, { error: true });
    } finally {
      ocupado = false;
      btnGuardar.disabled = false;
    }
  }

  async function deshacer() {
    if (!ultimoGuardado || ocupado) return;
    ocupado = true;
    try {
      const datos = await pedir("/api/deshacer", ultimoGuardado);
      mostrarConteo(datos.conteo);
      avisar("Se borró el último dibujo de " + CLASES[ultimoGuardado.clase] + ".");
      ultimoGuardado = null;
    } catch (err) {
      avisar(err.message, { error: true });
    } finally {
      ocupado = false;
    }
  }

  async function cambiar() {
    try {
      borrar();
      mostrarSigno(await cargarEstado(claseActual));
    } catch (err) {
      avisar(err.message, { error: true });
    }
  }

  btnBorrar.addEventListener("click", borrar);
  btnGuardar.addEventListener("click", guardar);
  btnCambiar.addEventListener("click", cambiar);
  btnDeshacer.addEventListener("click", deshacer);

  document.addEventListener("keydown", function (e) {
    if (e.target === inputAutor) return;
    // Enter sobre un botón enfocado hace lo de ese botón, no guardar
    if (e.key === "Enter" && e.target.tagName !== "BUTTON") { e.preventDefault(); guardar(); }
    if (e.key === "Escape") { e.preventDefault(); borrar(); }
  });

  // ---------- inicio
  cargarEstado()
    .then(mostrarSigno)
    .catch(function (err) {
      mostrarSigno(Object.keys(CLASES)[0]);
      avisar(err.message, { error: true });
    });
})();
