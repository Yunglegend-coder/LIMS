document.addEventListener("DOMContentLoaded", function () {

    const farmField = document.getElementById("id_farm");
    const houseField = document.getElementById("id_house");

    if (!farmField || !houseField) {
        return;
    }

    farmField.addEventListener("change", function () {

        const farmId = this.value;

        houseField.innerHTML = "";

        const blank = document.createElement("option");
        blank.value = "";
        blank.textContent = "---------";
        houseField.appendChild(blank);

        if (!farmId) {
            return;
        }

        fetch(`/locations/houses/?farm=${farmId}`)
            .then(response => response.json())
            .then(data => {

                data.forEach(function (house) {

                    const option = document.createElement("option");

                    option.value = house.id;
                    option.textContent = house.name;

                    houseField.appendChild(option);

                });

            });

    });

});