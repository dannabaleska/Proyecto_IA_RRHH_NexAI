(() => {
  const chatLog = document.getElementById("chat-log");
  const chatLogInner = chatLog.querySelector(".chat-log-inner");
  const form = document.getElementById("form-chat");
  const input = document.getElementById("input-pregunta");
  const waiting = document.getElementById("indicador-espera");
  const btnReiniciar = document.getElementById("btn-reiniciar");
  const btnEnviar = form.querySelector(".btn-enviar");

  const tplUsuario = document.getElementById("tpl-mensaje-usuario");
  const tplBot = document.getElementById("tpl-mensaje-bot");
  const tplError = document.getElementById("tpl-mensaje-error");

  if (window.marked) {
    marked.setOptions({ breaks: true });
  } else {
    console.warn("marked.js no se cargó; las respuestas se mostrarán como texto plano.");
  }

  function renderizarMarkdown(texto) {
    if (window.marked) return marked.parse(texto);
    const parrafo = document.createElement("p");
    parrafo.textContent = texto;
    return parrafo.outerHTML;
  }

  // Historial solo visual: el backend (orchestrator.responder) es stateless,
  // cada pregunta se envía sola, sin contexto de mensajes previos.
  function agregarMensajeUsuario(texto) {
    const nodo = tplUsuario.content.cloneNode(true);
    nodo.querySelector("p").textContent = texto;
    chatLogInner.appendChild(nodo);
  }

  function agregarMensajeBot(resultado) {
    const nodo = tplBot.content.cloneNode(true);
    const wrapper = nodo.querySelector(".msg-bot");
    nodo.querySelector(".msg-texto").innerHTML = renderizarMarkdown(resultado.respuesta || "");

    const agentes = resultado.agentes_participantes || [];
    const fuentes = resultado.fuentes || [];
    const detalle = nodo.querySelector(".detalle-fuentes");

    if (agentes.length > 0 || fuentes.length > 0) {
      detalle.hidden = false;

      const agentesLista = nodo.querySelector(".agentes-lista");
      agentes.forEach((nombreAgente) => {
        const badge = document.createElement("span");
        badge.className = "badge-agente";
        badge.textContent = nombreAgente;
        agentesLista.appendChild(badge);
      });

      const fuentesLista = nodo.querySelector(".fuentes-lista");
      if (fuentes.length > 0) {
        fuentes.forEach((fragmento) => {
          const li = document.createElement("li");
          li.textContent = fragmento;
          fuentesLista.appendChild(li);
        });
      } else {
        const li = document.createElement("li");
        li.textContent = "Esta acción no cita fragmentos documentales.";
        fuentesLista.appendChild(li);
      }
    }

    chatLogInner.appendChild(nodo);

// Actualiza la lista si se registró una nueva solicitud.
    if (agentes.includes(NOMBRE_AGENTE_ACCION)) {
      cargarSolicitudes(true);
    }

    return wrapper;
  }

  function agregarMensajeError(texto) {
    const nodo = tplError.content.cloneNode(true);
    nodo.querySelector("p").textContent = texto;
    chatLogInner.appendChild(nodo);
  }

  function desplazarAlFinal() {
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  function ajustarAlturaTextarea() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 140) + "px";
  }

  input.addEventListener("input", ajustarAlturaTextarea);

  input.addEventListener("keydown", (evento) => {
    if (evento.key === "Enter" && !evento.shiftKey) {
      evento.preventDefault();
      form.requestSubmit();
    }
  });

  async function enviarPregunta(pregunta) {
    const respuestaHttp = await fetch("/consultar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pregunta }),
    });

    if (!respuestaHttp.ok) {
      let detalle = "No se pudo procesar la consulta.";
      try {
        const cuerpoError = await respuestaHttp.json();
        detalle = cuerpoError.detail || detalle;
      } catch (_error) {
        // Se conserva el mensaje genérico si el cuerpo no es JSON válido.
      }
      throw new Error(detalle);
    }

    return respuestaHttp.json();
  }

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const pregunta = input.value.trim();
    if (!pregunta) return;

    agregarMensajeUsuario(pregunta);
    input.value = "";
    ajustarAlturaTextarea();
    desplazarAlFinal();

    btnEnviar.disabled = true;
    waiting.hidden = false;
    desplazarAlFinal();

    try {
      const resultado = await enviarPregunta(pregunta);
      agregarMensajeBot(resultado);
    } catch (error) {
      agregarMensajeError(
        "No pude conectarme con la mesa de ayuda en este momento. " +
        "Intenta de nuevo en unos segundos. (" + error.message + ")"
      );
    } finally {
      waiting.hidden = true;
      btnEnviar.disabled = false;
      desplazarAlFinal();
      input.focus();
    }
  });

  btnReiniciar.addEventListener("click", () => {
    const mensajes = chatLogInner.querySelectorAll(".msg");
    // Conserva solo el primer mensaje (el saludo inicial del asistente).
    mensajes.forEach((mensaje, indice) => {
      if (indice > 0) mensaje.remove();
    });
    input.value = "";
    ajustarAlturaTextarea();
    input.focus();
  });

// ---------- Solicitudes registradas (solo lectura) ----------
// Consulta el endpoint GET /solicitudes para mostrar los registros existentes.

  const NOMBRE_AGENTE_ACCION = "Agente de Acción (Registro de Solicitudes)";
  const acordeonSolicitudes = document.getElementById("acordeon-solicitudes");
  const contenedorSolicitudes = document.getElementById("solicitudes-contenido");
  let solicitudesCargadasUnaVez = false;

  function renderizarSolicitudes(solicitudes) {
    contenedorSolicitudes.innerHTML = "";

    if (!solicitudes || solicitudes.length === 0) {
      const vacio = document.createElement("p");
      vacio.className = "solicitudes-vacio";
      vacio.textContent = "Aún no hay solicitudes registradas.";
      contenedorSolicitudes.appendChild(vacio);
      return;
    }

    solicitudes.forEach((solicitud) => {
      const card = document.createElement("div");
      card.className = "solicitud-card";

      const header = document.createElement("div");
      header.className = "solicitud-card-header";

      const tipo = document.createElement("span");
      tipo.className = "solicitud-tipo";
      tipo.textContent = solicitud.tipo_solicitud || "—";

      const id = document.createElement("span");
      id.className = "solicitud-id";
      id.textContent = "ID " + (solicitud.id || "—");

      header.appendChild(tipo);
      header.appendChild(id);
      card.appendChild(header);

      const fecha = document.createElement("p");
      fecha.className = "solicitud-fecha";
      fecha.textContent = solicitud.fecha_hora || "";
      card.appendChild(fecha);

      const listaDatos = document.createElement("ul");
      listaDatos.className = "solicitud-datos";
      const datos = solicitud.datos || {};
      Object.keys(datos).forEach((campo) => {
        const li = document.createElement("li");

        const campoSpan = document.createElement("span");
        campoSpan.className = "campo";
        campoSpan.textContent = campo;

        const valorSpan = document.createElement("span");
        valorSpan.className = "valor";
        valorSpan.textContent = datos[campo];

        li.appendChild(campoSpan);
        li.appendChild(valorSpan);
        listaDatos.appendChild(li);
      });
      card.appendChild(listaDatos);

      contenedorSolicitudes.appendChild(card);
    });
  }

  async function cargarSolicitudes(forzar) {
    if (solicitudesCargadasUnaVez && !forzar) return;
    try {
      const respuestaHttp = await fetch("/solicitudes");
      if (!respuestaHttp.ok) throw new Error("Respuesta no válida del servidor.");
      const cuerpo = await respuestaHttp.json();
      renderizarSolicitudes(cuerpo.solicitudes || []);
      solicitudesCargadasUnaVez = true;
    } catch (_error) {
      contenedorSolicitudes.innerHTML =
        '<p class="solicitudes-vacio">No se pudieron cargar las solicitudes registradas.</p>';
    }
  }

  acordeonSolicitudes.addEventListener("toggle", () => {
    if (acordeonSolicitudes.open) cargarSolicitudes(false);
  });

  input.focus();
})();
