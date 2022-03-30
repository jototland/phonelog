let current_language = "en"
try {
    if (navigator.language.substring(0, 2).toLowerCase() in ['no', 'nb', 'nn']) {
        current_language = "no"
    }
} catch (_) {}

translations = {
    'no': {
        "Phone log": "Telefonlogg",
        "Menu": "Meny",
        "Live": "Sanntid",
        "History": "Historisk",
        "Customer data": "Kundedata",
        "Contacts": "Kontakter",
        "Users": "Brukere",
        "New user": "Ny bruker",
        "No answer after": "Ingen svar etter",
        "seconds": "sekunder",
        "Change password": "Bytt passord",
        "Logout": "Logg ut",
        "Show blocked numbers": "Vis blokkerte numre",
        "Disconnected": "Frakoblet",
        "Not connected": "Ikke tilkoblet",
        "Connected": "Tilkoblet",
        "Connected since:": "Tilkoblet siden: ",
        "Waiting for data": "Venter på data",
        "Subscribing": "Tilkobler",
        "Subscribing to live view data": "Oppretter abonnement på sanntidsdata",
        "Disconnected since:": "Frakoblet siden: ",
        "Reason:": "Årsak: ",
        "Message:": "Melding: ",
        "Last reconnect attempt:": "Siste tilkoblingsforsøk: ",
        "Last update:": "Siste oppdatering: ",
        "Incoming call": "Innkommende samtale",
        "Outgoing call": "Utgående samtale",
        "Toggle detailed view": "Vis detaljer",
        "External phone line": "Ekstern telefonlinje",
        "Agent name and phone": "Agentens navn og tlfnr",
        "Copy to clipboard": "Kopier til utklippstavlen",
        "Search for number in 1881.no": "Søk på 1881.no",
        "Search for number in hitta.se": "Søk på hitta.se",
        "Search for number 118.dk": "Søk på 188.dk",
    }
}

const translate = (text) => {
    try {
        translation = translations[current_language][text.trim()]
        return translation || text
    } catch (e) {
        return text
    }
}

const fix_i18n = (start=document) => {
    for (let el of start.querySelectorAll('[data-title-i18n]')) {
        el.setAttribute('title', translate(el.dataset.titleI18n))
    }
    for (let el of start.querySelectorAll('[data-i18n]')) {
        el.innerText = translate(el.innerText)
    }
}

const local_format = Intl.DateTimeFormat()
const fmt_epoch_as = (epoch, what) => {
    const date = new Date(epoch * 1000)
    const year = String(1900 + date.getYear()).padStart(4, '0')
    const month = String(1 + date.getMonth()).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hour = String(date.getHours()).padStart(2, '0')
    const minute = String(date.getMinutes()).padStart(2, '0')
    const second = String(date.getSeconds()).padStart(2, '0')
    switch(what) {
        case 'iso_datetime':
            return year + '-' + month + '-' + day + ' ' + hour + ':' + minute + ':' + second
        case 'iso_time':
            return hour + ':' + minute + ':' + second
        case 'iso_date':
            return year + '-' + month + '-' + day
        case 'local_date':
            return local_format.format(epoch*1000)
        case 'local_time':
            return new Date(epoch*1000).toLocaleTimeString()
        case 'local_datetime':
            return local_format.format(epoch*1000) + ' ' +
                new Date(epoch*1000).toLocaleTimeString()
        case 'local_date_iso_time':
            return local_format.format(epoch*1000) + ' ' + hour + ':' + minute + ':' + second
    }
}

const fix_dates = (start=document) => {
    for (let format of [
        'iso_date', 'iso_time', 'iso_datetime',
        'local_date', 'local_time', 'local_datetime',
        'local_date_iso_time']) {
        for (let el of start.querySelectorAll('.fix_' + format)) {
            if (el.dataset.epoch) {
                el.textContent = fmt_epoch_as(el.dataset.epoch, format)
                el.style.visibility = 'visible'
            }
        }
    }
}

const fix_tooltips = (start=document, classes='') => {
    for (let el of start.querySelectorAll('[data-tooltip]')) {
        new bootstrap.Tooltip(el, { customClass: classes})
        el.addEventListener('click', () => {
            bootstrap.Tooltip.getOrCreateInstance(el).hide()
        })
    }
    for (let el of start.querySelectorAll('[data-tooltip-container-body]')) {
        new bootstrap.Tooltip(el , { container: 'body', customClass: classes })
        el.addEventListener('click', () => {
            bootstrap.Tooltip.getOrCreateInstance(el).hide()
        })
    }
}

const unhide = () => {
    for (let el of document.querySelectorAll('.call-session')) {
        el.classList.remove('d-none')
    }
}


const hide_blocked_calls = () => {
    for (let el of document.querySelectorAll('.call-session.blocked-invalid-number')) {
        el.classList.add('d-none')
    }
}

const hide_blocked_calls_unless_checked = () => {
    checkbox = document.getElementById('show_blocked_checkbox')
    if (!checkbox || !checkbox.checked) {
        hide_blocked_calls()
    } else {
        unhide()
    }
}

const fix_all = (start=document) => {
    fix_i18n()
    fix_dates()
    fix_tooltips()
    hide_blocked_calls_unless_checked()
}

document.addEventListener('DOMContentLoaded', () => {
    show_blocked_checkbox = document.getElementById('show_blocked_checkbox')
    if (show_blocked_checkbox) {
        show_blocked_checkbox.addEventListener('change', () => {
            hide_blocked_calls_unless_checked()
        })
    }
})

document.addEventListener('DOMContentLoaded', () => {
    fix_all()
})
