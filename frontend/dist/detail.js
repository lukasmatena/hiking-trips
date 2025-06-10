"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
function createPage(tripDetail) {
    return __awaiter(this, void 0, void 0, function* () {
        let title = document.getElementById("titleElement");
        let desc = document.getElementById("descriptionElement");
        let prev = document.getElementById("prevTripElement");
        let next = document.getElementById("nextTripElement");
        title.textContent = tripDetail.title;
        desc.textContent = tripDetail.description;
        prev.href = tripDetail.prev_trip_id ? "detail.html?trip_id=" + tripDetail.prev_trip_id.toString() : "";
        next.href = tripDetail.next_trip_id ? "detail.html?trip_id=" + tripDetail.next_trip_id.toString() : "";
        let photosElement = document.getElementById("photosElement");
        const photoUrls = tripDetail.urls;
        for (let i = 0; i < photoUrls.length; ++i) {
            const photoTitleText = "photo number " + i.toString();
            const photoUrl = photoUrls[i];
            let photoLink = document.createElement("a");
            let photoImage = document.createElement("img");
            photoImage.src = photoUrl;
            photoImage.title = photoTitleText;
            photoImage.alt = photoTitleText;
            photoLink.href = photoUrl;
            let brElement = document.createElement("br");
            photoLink.appendChild(photoImage);
            photosElement.appendChild(photoLink);
            photosElement.appendChild(brElement);
        }
    });
}
function readTripData(trip_id) {
    return __awaiter(this, void 0, void 0, function* () {
        const apiUrl = "api/trips/" + trip_id.toString();
        const response = yield fetch(apiUrl);
        if (!response.ok)
            throw new Error("Error fetching data (" + response.status.toString() + ": " + response.statusText);
        return response;
    });
}
function loadTrip(trip_id) {
    readTripData(trip_id)
        .then((tripDetail) => __awaiter(this, void 0, void 0, function* () {
        yield createPage(yield tripDetail.json());
    }))
        .catch((error) => {
        console.log(error);
    });
}
function parseTripId() {
    const queryStr = window.location.search;
    const params = new URLSearchParams(queryStr);
    const trip_str = params.get("trip_id");
    if (trip_str == null)
        throw new Error("Invalid trip number");
    const trip_id = parseInt(trip_str, 10);
    if (isNaN(trip_id))
        throw new Error("Invalid trip number");
    return trip_id;
}
try {
    const trip_id = parseTripId();
    loadTrip(trip_id);
}
catch (error) {
    console.log(error);
}
