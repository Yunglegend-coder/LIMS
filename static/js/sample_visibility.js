document.addEventListener("DOMContentLoaded", function () {

    const sampleType = document.getElementById("id_sample_type");

    if (!sampleType) {
        return;
    }

    const wrappers = {
        history: document.getElementById("history-wrapper"),
        source_of_birds: document.getElementById("source_of_birds-wrapper"),
        source_of_water: document.getElementById("source_of_water-wrapper"),
        feed_type: document.getElementById("feed_type-wrapper"),
        last_vaccination: document.getElementById("last_vaccination-wrapper"),
        antibiotics_used: document.getElementById("antibiotics_used-wrapper"),
        mortality_pattern: document.getElementById("mortality_pattern-wrapper"),
        pathology: document.getElementById("pathology-wrapper"),
        remarks: document.getElementById("remarks-wrapper"),
    };


    function hideAll() {

        Object.values(wrappers).forEach(function (wrapper) {

            if (wrapper) {
                wrapper.style.display = "none";
            }

        });

    }


    function show(fieldNames) {

        fieldNames.forEach(function (fieldName) {

            const wrapper = wrappers[fieldName];

            if (wrapper) {
                wrapper.style.display = "";
            }

        });

    }


    function updateFields() {

        hideAll();

        const selectedType = sampleType.value;

        switch (selectedType) {

            /*
             * CARCASS / DOC TISSUE
             */
            case "CARCASS":
            case "DOC_TISSUE":

                show([
                    "history",
                    "source_of_birds",
                    "source_of_water",
                    "feed_type",
                    "last_vaccination",
                    "antibiotics_used",
                    "mortality_pattern",
                    "pathology",
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
                    "history",
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