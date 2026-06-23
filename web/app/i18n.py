"""
Lightweight i18n. Templates keep the Spanish text as the key; for English we
look it up in EN (falling back to the Spanish key when a translation is
missing). Language is resolved per-request (cookie / ?lang=) in middleware.
"""
from __future__ import annotations

LANGS = ("es", "en")
DEFAULT = "es"

# Spanish key -> English. Anything not here simply shows the Spanish text.
EN: dict[str, str] = {
    # nav / footer
    "Habitaciones": "Rooms",
    "Opiniones": "Reviews",
    "Contacto": "Contact",
    "Reservar": "Book",
    "Navegación": "Navigation",
    "Síguenos": "Follow us",
    "Hecho con cariño · Reserva directa": "Made with care · Direct booking",
    "Inicio": "Home",

    # hero
    "Un refugio de calma": "A peaceful retreat",
    "en el corazón de Cartagena": "in the heart of Cartagena",
    "Casa Gracia es un hotel boutique de 8 habitaciones recién renovadas, con piscina y atención cálida, a pasos del Castillo de San Felipe.":
        "Casa Gracia is a boutique hotel with 8 newly renovated rooms, a pool and warm service, steps from San Felipe Castle.",
    "Reservar ahora": "Book now",
    "Ver habitaciones": "View rooms",

    # booking bar
    "Habitación": "Room",
    "Cualquiera": "Any",
    "Entrada": "Check-in",
    "Salida": "Check-out",
    "Huéspedes": "Guests",
    "Buscar": "Search",

    # intro
    "Bienvenido a Casa Gracia": "Welcome to Casa Gracia",
    "Hospitalidad cartagenera, comodidad contemporánea": "Cartagena hospitality, contemporary comfort",
    "Recién renovado en el tranquilo barrio de Manga, nuestro hotel combina el encanto de una casa cartagenera con el confort de habitaciones modernas. Disfruta de la piscina, la terraza y un servicio personalizado que hará de tu estadía algo memorable.":
        "Newly renovated in the quiet Manga neighborhood, our hotel blends the charm of a Cartagena home with the comfort of modern rooms. Enjoy the pool, the terrace and personalized service that makes your stay memorable.",
    "A 7 minutos a pie del Castillo de San Felipe de Barajas y a pocos minutos del Centro Histórico amurallado.":
        "A 7-minute walk from San Felipe de Barajas Castle and minutes from the walled Old Town.",
    "Conoce el hotel": "About the hotel",

    # features
    "Lo que te espera": "What awaits you",
    "Pensado para tu descanso": "Designed for your rest",
    "Piscina": "Pool",
    "Piscina al aire libre y plunge pool todo el año.": "Outdoor pool and plunge pool year-round.",
    "WiFi gratis": "Free WiFi",
    "Conexión rápida en todo el hotel.": "Fast connection throughout the hotel.",
    "Parqueo": "Parking",
    "Estacionamiento privado gratuito.": "Free private parking.",
    "Terraza": "Terrace",
    "Zona de descanso al aire libre y solárium.": "Outdoor lounge area and sun deck.",

    # rooms section
    "Alojamiento": "Accommodation",
    "Nuestras habitaciones": "Our rooms",
    "Ver todas las habitaciones": "View all rooms",

    # reviews section
    "Lo que dicen nuestros huéspedes": "What our guests say",
    "{n} opiniones": "{n} reviews",
    "Ver todas las opiniones": "View all reviews",

    # location
    "Ubicación": "Location",
    "En Manga, a pasos de todo": "In Manga, steps from everything",
    "7 min al Castillo de San Felipe": "7 min to San Felipe Castle",
    "5 min a Portal de San Felipe": "5 min to Portal de San Felipe",
    "~1.6 km al Centro Histórico": "~1.6 km to the Old Town",
    "~10 min al aeropuerto": "~10 min to the airport",
    "Reservar mi estadía": "Book my stay",

    # room card / detail
    "huésp.": "guests",
    "Ver": "View",
    "por noche": "per night",
    "Sobre esta habitación": "About this room",
    "Hasta {n} huéspedes": "Up to {n} guests",
    "Comodidades": "Amenities",
    "Comprobar disponibilidad": "Check availability",
    "Apartas tu fecha al confirmar.": "Your dates are held on confirmation.",

    # booking page
    "Reserva directa · mejor precio": "Direct booking · best price",
    "Completa tu reserva": "Complete your booking",
    "Selecciona una habitación…": "Select a room…",
    "Teléfono / WhatsApp": "Phone / WhatsApp",
    "Nombre completo": "Full name",
    "Correo electrónico": "Email",
    "Notas (opcional)": "Notes (optional)",
    "Hora de llegada, peticiones especiales…": "Arrival time, special requests…",
    "Continuar al pago": "Continue to booking",
    "Al continuar apartamos tu habitación por 20 minutos mientras completas el pago seguro con Wompi.":
        "When you continue we hold your room for 20 minutes while you complete your booking.",
    "máx {n}": "max {n}",

    # checkout
    "Paso final": "Final step",
    "Confirma y paga": "Confirm your booking",
    "Reserva": "Booking",
    "Resumen de tu reserva": "Your booking summary",
    "Noches": "Nights",
    "Huésped": "Guest",
    "Total a pagar": "Total",
    "El pago en línea estará disponible muy pronto.": "Online payment will be available soon.",
    "Por ahora coordinamos el pago de forma personalizada para confirmar tu estadía. Escríbenos con tu referencia y te ayudamos enseguida.":
        "For now we arrange payment personally to confirm your stay. Message us with your reference and we'll help right away.",
    "Coordinar pago por WhatsApp": "Arrange payment via WhatsApp",
    "Ver mi reserva": "View my booking",

    # result
    "¡Reserva confirmada!": "Booking confirmed!",
    "Tu pago fue aprobado. Te enviamos los detalles a {email}.":
        "Your payment was approved. We've sent the details to {email}.",
    "¡Reserva registrada!": "Booking received!",
    "Tu reserva quedó registrada como pendiente. Te contactaremos para coordinar el pago y confirmarla. También puedes escribirnos por WhatsApp con tu referencia.":
        "Your booking is registered as pending. We'll contact you to arrange payment and confirm it. You can also message us on WhatsApp with your reference.",
    "No pudimos confirmar el pago": "We couldn't confirm the payment",
    "Tu reserva no se completó. Puedes intentar de nuevo o escribirnos por WhatsApp.":
        "Your booking wasn't completed. You can try again or message us on WhatsApp.",
    "Referencia": "Reference",
    "Fechas": "Dates",
    "Total": "Total",
    "Continuar / coordinar pago": "Continue / arrange payment",
    "Volver al inicio": "Back to home",

    # reviews page
    "Experiencias": "Experiences",
    "Opiniones de huéspedes": "Guest reviews",
    "Comparte tu experiencia": "Share your experience",
    "Nombre": "Name",
    "País": "Country",
    "Calificación": "Rating",
    "★★★★★ Excelente": "★★★★★ Excellent",
    "★★★★ Muy bueno": "★★★★ Very good",
    "★★★ Bueno": "★★★ Good",
    "★★ Regular": "★★ Fair",
    "★ Malo": "★ Poor",
    "Habitación (opcional)": "Room (optional)",
    "General": "General",
    "Título": "Title",
    "Una estadía encantadora": "A lovely stay",
    "Tu opinión": "Your review",
    "Publicar opinión": "Post review",
    "Aún no hay opiniones. ¡Sé el primero en compartir tu experiencia!":
        "No reviews yet. Be the first to share your experience!",

    # contact
    "Estamos para ayudarte": "We're here to help",
    "Contacto y ubicación": "Contact & location",
    "Teléfono:": "Phone:",
    "Correo:": "Email:",
    "Escríbenos": "Message us",
    "Cómo llegar": "Getting here",
    "A 7 min a pie del Castillo de San Felipe de Barajas, 5 min del Portal de San Felipe y a pocos minutos del Centro Histórico amurallado.":
        "A 7-min walk from San Felipe de Barajas Castle, 5 min from Portal de San Felipe and minutes from the walled Old Town.",

    # controlled vocab (amenities / bed / view)
    "Aire acondicionado": "Air conditioning",
    "Baño privado": "Private bathroom",
    "TV satelital": "Satellite TV",
    "Minibar": "Minibar",
    "Escritorio": "Desk",
    "Secador": "Hair dryer",
    "Caja fuerte": "Safe",
    "1 cama Queen": "1 Queen bed",
    "1 cama Doble": "1 Double bed",
    "1 cama King": "1 King bed",
    "2 camas dobles": "2 Double beds",
    "Interior": "Interior",
    "Exterior": "Exterior view",
    "Vista a la piscina": "Pool view",

    # route / system messages
    "Habitación no encontrada.": "Room not found.",
    "Reserva no encontrada.": "Booking not found.",
    "La fecha de salida debe ser posterior a la de entrada.": "The check-out date must be after the check-in date.",
    "Esas fechas ya no están disponibles para esta habitación.": "Those dates are no longer available for this room.",
    "Revisa los datos del formulario.": "Please check the form details.",
    "Esta habitación admite máximo {n} huéspedes.": "This room allows a maximum of {n} guests.",
    "Revisa los datos de tu opinión (calificación 1-5 y comentario).": "Please check your review (rating 1-5 and a comment).",
    "¡Gracias! Tu opinión fue publicada.": "Thank you! Your review has been published.",
    "¡Gracias! Tu opinión será publicada tras una breve revisión.": "Thank you! Your review will be published after a short review.",
    "No encontramos la página que buscas.": "We couldn't find the page you're looking for.",
    "Tuvimos un problema procesando tu solicitud. Intenta de nuevo en unos momentos.":
        "We had a problem processing your request. Please try again in a moment.",

    # chatbot widget
    "Asistente": "Assistant",
    "Asistente del hotel": "Hotel assistant",
    "en línea": "online",
    "Hola, soy el asistente de Casa Gracia. ¿En qué puedo ayudarte?":
        "Hi, I'm the Casa Gracia assistant. How can I help you?",
    "Escribe tu mensaje…": "Type your message…",
    "Enviar": "Send",
    "Cerrar": "Close",
    "Abrir chat": "Open chat",
    "escribiendo…": "typing…",
    "Error de conexión. Intenta de nuevo.": "Connection error. Please try again.",

    # JS (front-end) strings
    "Selecciona tus fechas": "Select your dates",
    "Comprobando…": "Checking…",
    "✓ ¡Disponible para tus fechas!": "✓ Available for your dates!",
    "Reservar estas fechas": "Book these dates",
    "No disponible para esas fechas. Prueba otras.": "Not available for those dates. Try others.",
    "No disponible": "Not available",
    "No pudimos comprobar ahora. Intenta de nuevo.": "We couldn't check right now. Please try again.",
    "Reintentar": "Retry",
    "noche(s)": "night(s)",
}

# Per-room English name/description (keyed by id_hab). Falls back to DB Spanish.
ROOM_EN: dict[str, dict[str, str]] = {
    "101": {"name": "Comfort Queen Room",
            "desc": "Cozy, newly renovated room with a Queen bed, air conditioning and "
                    "a private bathroom. Ideal for couples seeking calm, steps from San Felipe Castle."},
    "301": {"name": "Comfort Queen Superior Room",
            "desc": "Upper-floor Queen room, bright and quiet, with all modern comforts and pool access."},
    "201": {"name": "Standard Double Room",
            "desc": "Comfortable double room with a full bed, perfect for a getaway in Cartagena."},
    "102": {"name": "Large Double Room",
            "desc": "A roomier version of our double, with extra sitting space and a work area."},
    "202": {"name": "Deluxe King Room · Pool View",
            "desc": "Our flagship room: a King bed, direct pool view and a serene atmosphere for a special stay."},
    "203": {"name": "Family Quadruple Room",
            "desc": "Spacious room with two double beds for families or groups of up to 4, without compromising comfort."},
}


def t(text: str, lang: str = DEFAULT) -> str:
    if lang == "en":
        return EN.get(text, text)
    return text


def room_name(room, lang: str) -> str:
    if lang == "en":
        return ROOM_EN.get(room.id_hab, {}).get("name", room.nom_hab)
    return room.nom_hab


def room_desc(room, lang: str) -> str:
    if lang == "en":
        return ROOM_EN.get(room.id_hab, {}).get("desc", room.description)
    return room.description


def get_lang(request) -> str:
    lang = getattr(getattr(request, "state", None), "lang", None)
    if lang in LANGS:
        return lang
    q = request.query_params.get("lang") if hasattr(request, "query_params") else None
    if q in LANGS:
        return q
    c = request.cookies.get("lang") if hasattr(request, "cookies") else None
    return c if c in LANGS else DEFAULT


# JS-facing strings bundled into window.I18N (see base.html).
JS_KEYS = [
    "Selecciona tus fechas", "Comprobando…", "✓ ¡Disponible para tus fechas!",
    "Reservar estas fechas", "No disponible para esas fechas. Prueba otras.",
    "No disponible", "No pudimos comprobar ahora. Intenta de nuevo.",
    "Reintentar", "Comprobar disponibilidad", "noche(s)",
]


def js_bundle(lang: str) -> dict[str, str]:
    return {k: t(k, lang) for k in JS_KEYS}
