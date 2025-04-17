document.addEventListener("DOMContentLoaded", function () {
    const addressInput = document.getElementById("id_address");
    const latInput = document.getElementById("id_latitude");
    const lonInput = document.getElementById("id_longitude");

    const mapContainer = document.createElement("div");
    mapContainer.id = "yandex-map";
    mapContainer.style = "width: 100%; height: 300px; margin-top: 10px;";
    addressInput.parentElement.appendChild(mapContainer);

    const script = document.createElement("script");
    script.src = "https://api-maps.yandex.ru/2.1/?lang=ru_RU&apikey=5e50de3d-ee8e-4918-a10f-106a707e6fac";
    script.onload = initMap;
    document.body.appendChild(script);

    function initMap() {
        ymaps.ready(function () {
            const map = new ymaps.Map("yandex-map", {
                center: [55.751574, 37.573856],
                zoom: 10,
                controls: ["searchControl"]
            });

            let placemark;
            const searchControl = map.controls.get("searchControl");

            function updatePlacemark(coords, address) {
                if (!placemark) {
                    placemark = new ymaps.Placemark(coords, {}, { draggable: true });
                    map.geoObjects.add(placemark);
                    placemark.events.add("dragend", function () {
                        const newCoords = placemark.geometry.getCoordinates();
                        updateCoords(newCoords);
                    });
                } else {
                    placemark.geometry.setCoordinates(coords);
                }

                addressInput.value = address;
                updateCoords(coords);
                map.setCenter(coords, 16);
            }

            function updateCoords(coords) {
                latInput.value = coords[0].toFixed(6);
                lonInput.value = coords[1].toFixed(6);
            }

            searchControl.events.add("resultselect", function (e) {
                const index = e.get("index");
                searchControl.getResult(index).then(function (result) {
                    const coords = result.geometry.getCoordinates();
                    const address = result.getAddressLine();
                    updatePlacemark(coords, address);
                });
            });

            // Если координаты уже есть — показать метку
            if (latInput.value && lonInput.value) {
                const coords = [parseFloat(latInput.value), parseFloat(lonInput.value)];
                updatePlacemark(coords, addressInput.value);
            } else if (addressInput.value) {
                ymaps.geocode(addressInput.value).then(function (res) {
                    const firstGeo = res.geoObjects.get(0);
                    if (firstGeo) {
                        const coords = firstGeo.geometry.getCoordinates();
                        updatePlacemark(coords, firstGeo.getAddressLine());
                    }
                });
            }
        });
    }
});
