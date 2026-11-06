document.addEventListener("DOMContentLoaded", function () {

    const sampleType = document.getElementById("id_sample_type");

    if (!sampleType) {
        return;
    }

    const wrappers = {
        doc_subtypes: document.getElementById("doc_subtypes-wrapper"),
        age: document.getElementById("age-wrapper"),
        breed_species: document.getElementById("breed_species-wrapper"),
        source_of_birds: document.getElementById("source_of_birds-wrapper"),
        source_of_water: document.getElementById("source_of_water-wrapper"),
        feed_type: document.getElementById("feed_type-wrapper"),
        population: document.getElementById("population-wrapper"),
        housing: document.getElementById("housing-wrapper"),
        major_complaint: document.getElementById("major_complaint-wrapper"),
        last_vaccination: document.getElementById("last_vaccination-wrapper"),
        medication: document.getElementById("medication-wrapper"),
        vaccination_history: document.getElementById("vaccination_history-wrapper"),
        drugs: document.getElementById("drugs-wrapper"),
        vaccination: document.getElementById("vaccination-wrapper"),
        mortality_pattern: document.getElementById("mortality_pattern-wrapper"),
        remarks: document.getElementById("remarks-wrapper"),
    };


    function hideAll() {

        Object.values(wrappers).forEach(function (wrapper) {

            if (wrapper) {
                wrapper.style.display = "none";
                wrapper.hidden = true;
            }

        });

    }


    function show(fieldNames) {

        fieldNames.forEach(function (fieldName) {

            const wrapper = wrappers[fieldName];

            if (wrapper) {
                wrapper.style.display = "";
                wrapper.hidden = false;
            }

        });

    }


    function updateFields() {

        hideAll();

        const selectedType = sampleType.value;
        document.querySelectorAll('input[name="doc_subtypes"]').forEach(function (field) {
            field.required = selectedType === "DOC";
        });

        switch (selectedType) {

            /*
             * CARCASS / DOC TISSUE
             */
            case "CARCASS":

                show([
                    "age",
                    "breed_species",
                    "source_of_birds",
                    "feed_type",
                    "population",
                    "source_of_water",
                    "housing",
                    "major_complaint",
                    "mortality_pattern",
                    "medication",
                    "vaccination_history",
                    "drugs",
                    "vaccination",
                    "last_vaccination",
                    "remarks"
                ]);

                break;

            case "DOC":
                show([
                    "doc_subtypes",
                    "age",
                    "breed_species",
                    "source_of_birds",
                    "feed_type",
                    "population",
                    "source_of_water",
                    "housing",
                    "major_complaint",
                    "mortality_pattern",
                    "medication",
                    "vaccination_history",
                    "drugs",
                    "vaccination",
                    "last_vaccination",
                    "remarks"
                ]);
                break;


            /*
             * WATER
             */
            case "WATER":

                show([
                    "source_of_water",
                    "remarks"
                ]);

                break;


            /*
             * FEED
             */
            case "FEED":

                show([
                    "feed_type",
                    "remarks"
                ]);

                break;


            /*
             * SWAB / FLUFF
             */
            case "BOOT_SWAB":
            case "TRACHEAL_SWAB":
            case "CLOACAL_SWAB":
            case "FLUFF":

                show([
                    "remarks"
                ]);

                break;


            /*
             * OTHER SAMPLE TYPES
             */
            default:

                show([
                    "remarks"
                ]);

                break;
        }
    }


    sampleType.addEventListener("change", updateFields);

    // Run once when the page loads
    updateFields();

});
