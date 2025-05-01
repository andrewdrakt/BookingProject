window.addEventListener("load", function () {
    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1
    });

    document.querySelectorAll('.techno-card').forEach(card => {
        observer.observe(card);
    });
});
function showSection(id) {
    const sections = ['current', 'history', 'fines', 'settings'];
    sections.forEach(name => {
        document.getElementById('section-' + name).style.display = (name === id) ? 'block' : 'none';
    });

    const buttons = document.querySelectorAll(".profile-tabs .btn");
    buttons.forEach(btn => btn.classList.remove("active"));

    const activeButton = document.querySelector(`.profile-tabs .btn[onclick="showSection('${id}')"]`);
    if (activeButton) {
        activeButton.classList.add("active");
    }
}
ScrollReveal().reveal('.htmlclass',{ delay: 400 })
document.addEventListener("DOMContentLoaded", () => {
    showSection('current');
});
document.addEventListener("DOMContentLoaded", function() {

    fetch('/api/parking-lots/')
    .then(response => response.json())
    .then(data => {
        let parkingList = document.getElementById('parkingList');
        data.forEach(parking => {
            let div = document.createElement('div');
            div.classList.add('parking-card');
            div.innerHTML = `<h3>${parking.name}</h3>
                             <p>${parking.address}</p>
                             <button onclick="selectParking(${parking.id}, '${parking.address}')">Выбрать</button>`;
            parkingList.appendChild(div);
        });
    })
    .catch(error => console.error('Ошибка при загрузке парковок:', error));
});

function selectParking(parkingId, parkingAddress) {
    document.getElementById('bookingForm').style.display = 'block';
    document.getElementById('parkingAddress').textContent = parkingAddress;

}

document.getElementById('confirmBooking').addEventListener('click', function() {

    const bookingData = {
        parking_lot: 1,
        user: 1,
        start_time: new Date(),
        end_time: new Date(new Date().getTime() + 3600000)
    };

    fetch('/api/create-booking/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(bookingData)
    })
    .then(response => response.json())
    .then(data => {

        document.getElementById('barrierControl').style.display = 'block';
    })
    .catch(error => console.error('Ошибка бронирования:', error));
});


document.getElementById('openBarrierButton').addEventListener('click', function() {
    if (confirm('Вы действительно хотите открыть шлагбаум?')) {
        // Отправляем команду на открытие шлагбаума
        fetch('/api/barrier-command/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ booking_id: 1, command: 'open' }) // booking_id нужно получить из ранее сохранённого бронирования
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message || data.error);
        })
        .catch(error => console.error('Ошибка открытия шлагбаума:', error));
    }
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        let cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
