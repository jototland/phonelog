document.addEventListener('DOMContentLoaded', () => {
    const connection_info = document.getElementById('connection_info')
    const connection_warning = document.getElementById('connection_warning')
    const active_content = document.getElementById('active_content')
    const overlay = document.getElementById('viewport-overlay')
    const socket = io.connect()

    let connected_since = undefined
    let disconnected_since = undefined
    let last_update = undefined
    let last_reconnect_attempt = undefined
    let joined_live_view_clients = false
    let disconnect_message = undefined
    let disconnect_reason = undefined

    const timestamp = () => {
        const now = new Date()
        return (
            String(now.getHours()).padStart(2, '0') + ':' +
            String(now.getMinutes()).padStart(2, '0') + ':' +
            String(now.getSeconds()).padStart(2, '0')
        )
    }

    let update_connection_status = () => {
        let tooltip = ''
        connection_info.classList.remove("bg-danger")
        connection_info.classList.remove('bg-warning')
        connection_info.classList.remove("bg-success")
        if (connected_since) {
            connection_info.innerHTML = translate("Connected")
            tooltip = translate('Connected since: ') + connected_since
            if (joined_live_view_clients) {
                if (last_update) {
                    connection_info.classList.add("bg-success")
                    overlay.classList.remove('visible')
                } else {
                    connection_info.classList.add("bg-warning")
                    tooltip += translate("Waiting for data")
                }
            } else {
                connection_info.classList.add('bg-warning')
                connection_info.innerHTML = translate("Subscribing")
                tooltip = translate('Subscribing to live view data')
            }
        } else {
            connection_info.classList.add("bg-danger")
            connection_info.innerHTML = translate("Disconnected")
            overlay.classList.add('visible')
            tooltip = translate('Disconnected since: ') + disconnected_since
            if (disconnect_reason) {
                tooltip += '\n' + translate('Reason: ') + disconnect_reason
            }
            if (disconnect_message) {
                tooltip += '\n' + translate('Message: ') + disconnect_message
            }
            if (last_reconnect_attempt) {
                tooltip += '\n' + translate('Last reconnect attempt: ') + last_reconnect_attempt
            }
        }
        if (disconnect_message) {
            tooltip += '\n' + translate('Message: ') + disconnect_message
        }
        if (last_update) {
            tooltip += '\n' + translate('Last update: ') + last_update
        }

        connection_info.setAttribute('data-bs-original-title', tooltip)
        if (connection_info.getAttribute('aria-describedby')) {
            bootstrap.Tooltip.getOrCreateInstance(connection_info).show()
        }
    }

    socket.on('connect', () => {
        connected_since = timestamp()
        disconnected_since = undefined
        last_update = undefined
        last_reconnect_attempt = undefined
        joined_live_view_clients = false
        disconnect_message = undefined
        disconnect_reason = undefined
        update_connection_status()

        socket.emit('join_live_view_clients', csrf_token)
        socket.io.engine.on('upgrade', () => {
            if (socket.io.engine.transport.name != 'websocket') {
              connection_warning.innerHTML = 'Websockets not supported'
            }
        })
        document.body.style.bgcolor = undefined
    })


    socket.on('joined_live_view_clients', (_, cb) => {
        joined_live_view_clients = true
        update_connection_status()
        if (cb) cb()
    })


    socket.on('disconnect_message', (msg, cb) => {
        disconnect_message = msg
        update_connection_status()
        if (cb) cb()
    })


    socket.on('disconnect', (reason) => {
        connected_since = undefined
        disconnected_since = timestamp()
        update_connection_status()

        if (reason == 'io server disconnect') {
            disconnect_reason = 'disconnected by server'
            update_connection_status()
            // wait 10 seconds and reload page
            setTimeout(
                () => {window.location.href = window.location.href},
                10000)
        } else if (reason) {
            disconnect_reason = reason
            update_connection_status()
        }
    })


    socket.on('connect_error', () => {
        last_reconnect_attempt = timestamp()
        update_connection_status()
    })


    socket.on('replace_content', (msg, cb) => {
        last_update = timestamp()
        update_connection_status()

        for (let el of document.querySelectorAll('.tooltip.dynamic')) {
            el.remove()
        }

        old_expanded_ids = Array.from(
            active_content.querySelectorAll('.collapse.show[id^="details-"]')
        ).map(x => x.id)

        active_content.innerHTML = msg

        for (let id of old_expanded_ids) {
            let el = document.getElementById(id)
            if (el) {
                old_transition = el.style.transition
                el.style.transition = "none"
                bootstrap.Collapse.getOrCreateInstance(el).show()
                setTimeout(
                    () => { el.style.transition = old_transition },
                    500)
            }
        }

        fix_all()
        if (cb) cb()
    })

}) // DOMContentLoaded
