function calculateArea() {

    const length = Number(
        document.getElementById("length").value
    );

    const width = Number(
        document.getElementById("width").value
    );

    const unit = document.getElementById("areaUnit").value;

    if (!length || !width) {
        document.getElementById("areaResult").innerHTML =
            "Please enter length and width.";
        return;
    }

    const area = length * width;

    let result = "";

    if (unit === "sqft") {

        result = `
            Area: ${area.toFixed(2)} sq ft
            <br>
            ${(area / 43560).toFixed(4)} acres
            <br>
            ${(area * 0.092903).toFixed(2)} sq m
        `;

    } else if (unit === "sqm") {

        result = `
            Area: ${area.toFixed(2)} sq m
            <br>
            ${(area / 4046.856).toFixed(4)} acres
        `;

    } else if (unit === "acre") {

        result = `
            Area: ${area.toFixed(2)} acres
            <br>
            ${(area * 43560).toFixed(2)} sq ft
            <br>
            ${(area * 4046.856).toFixed(2)} sq m
        `;

    } else {

        result = `
            Area: ${area.toFixed(2)} hectares
            <br>
            ${(area * 2.47105).toFixed(4)} acres
        `;
    }

    document.getElementById("areaResult").innerHTML = result;
}