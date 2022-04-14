password_check = (password_field_1_id, password_field_2_id,
    password_diagnostics_1, password_diagnostics_2,
    password_submit_id, min_score=2) =>
{
    document.addEventListener('DOMContentLoaded', () => {
        const password1 = document.getElementById(password_field_1_id)
        const password2 = document.getElementById(password_field_2_id)
        const diag1 = document.getElementById(password_diagnostics_1)
        const diag2 = document.getElementById(password_diagnostics_2)
        const submit = document.getElementById(password_submit_id)

        const progress = document.createElement("div")
        progress.classList.add("progress")
        const progressbar = document.createElement('div')
        progressbar.classList.add("progress-bar")
        progress.appendChild(progressbar)
        diag1.appendChild(progress)

        const feedback_warning = document.createElement("div")
        feedback_warning.classList.add("text-danger")
        diag1.appendChild(feedback_warning)

        const feedback_suggestion = document.createElement("div")
        feedback_suggestion.classList.add("text-warning")
        diag1.appendChild(feedback_suggestion)

        const _guesses = document.createElement("div")
        const guesses = document.createElement("span")
        _guesses.innerText = "Estimated number of guesses: "
        _guesses.appendChild(guesses)
        diag1.appendChild(_guesses)

        const time_to_crack = document.createElement("div")
        time_to_crack.innerText = "Time needed to crack:"
        const ul = document.createElement("ul")
        time_to_crack.appendChild(ul)
        diag1.appendChild(time_to_crack)

        const _crack_online = document.createElement("li")
        _crack_online.innerText = "With a computer program guessing online: "
        const crack_online = document.createElement("span")
        _crack_online.appendChild(crack_online)
        ul.appendChild(_crack_online)

        const _crack_offline_li = document.createElement("li")
        const _crack_offline_small = document.createElement("small")
        _crack_offline_small.innerText = "With offline access to password hash and a fast computer: "
        const crack_offline = document.createElement("span")
        _crack_offline_li.appendChild(_crack_offline_small)
        _crack_offline_small.appendChild(crack_offline)
        ul.appendChild(_crack_offline_li)

        verify = () => {
            let result = zxcvbn(password1.value)

            if (result.score < min_score) {
                password1.classList.add("border", "border-danger", "border-2")
            } else {
                password1.classList.remove("border", "border-danger", "border-2")
            }

            progressbar.style = `width: ${100 * result.score/4}%`
            progressbar.innerText = `${100 * result.score/4}%`
            if (result.score < 2) {
                progressbar.classList.remove('bg-warning');
                progressbar.classList.remove('bg-success');
                progressbar.classList.add('bg-danger');
            } else if (result.score == 3) {
                progressbar.classList.remove('bg-success');
                progressbar.classList.remove('bg-danger');
                progressbar.classList.add('bg-warning');
            } else if (result.score == 4) {
                progressbar.classList.remove('bg-warning');
                progressbar.classList.remove('bg-danger');
                progressbar.classList.add('bg-success');
            }

            feedback_warning.innerText = result.feedback.warning || ''
            feedback_suggestion.innerText = result.feedback_suggestion || ''
            guesses.innerText = Math.round(result.guesses)
            crack_online.innerText = result.crack_times_display.online_no_throttling_10_per_second
            crack_offline.innerText = result.crack_times_display.offline_fast_hashing_1e10_per_second

            if (result.score >= min_score) {
                if (password1.value == password2.value) {
                    password2.classList.remove("border", "border-danger", "border-2")
                    diag2.innerText = "Passwords match!"
                    diag2.classList.add("text-success")
                    diag2.classList.remove("text-danger")
                } else {
                    password2.classList.add("border", "border-danger", "border-2")
                    diag2.innerText = "Passwords fail to match!"
                    diag2.classList.remove("text-success")
                    diag2.classList.add("text-danger")
                }
            } else {
                diag2.innerText = ""
            }

            submit.disabled = result.score < min_score || password1.value != password2.value
            // console.log(`Score: ${result.score}, equal: ${password1.value==password2.value}, min_score: ${min_score}`)
        }

        password1.addEventListener("keyup", verify)
        password2.addEventListener("keyup", verify)
        verify()
    })
}
