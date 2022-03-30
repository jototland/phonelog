const start_date = document.getElementById('start_date')

start_date.setAttribute(
    'value',
    new Date(start_date.dataset.from * 1000).toISOString().substring(0,10)
)


start_date.addEventListener("change", () => {
    from_epoch = (+new Date(start_date.value+"T00:00:00")) / 1000
    to_epoch = from_epoch + 24*60*60
    window.location.href =
        window.location.origin +
        window.location.pathname +
        '?from=' + from_epoch +
        '&to=' + to_epoch
})
