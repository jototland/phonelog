document.addEventListener('DOMContentLoaded', () => {
    const start_date = document.getElementById('start_date')
    const date = new Date(start_date.dataset.from * 1000)
    const year = String(1900 + date.getYear()).padStart(4, '0')
    const month = String(1 + date.getMonth()).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hour = date.getHours()
    const minute = date.getMinutes()
    const second = date.getSeconds()
    if (hour == 0 && minute == 0 && second == 0) {
        iso_date = year + '-' + month + '-' + day
        start_date.setAttribute('value', iso_date)
    }

    start_date.addEventListener("change", () => {
        from_epoch = (+new Date(start_date.value+"T00:00:00")) / 1000
        to_epoch = from_epoch + 24*60*60
        window.location.href =
            window.location.origin +
            window.location.pathname +
            '?from=' + from_epoch +
            '&to=' + to_epoch
    })
})


