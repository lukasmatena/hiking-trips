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
function createList(response) {
    return __awaiter(this, void 0, void 0, function* () {
        let tripsListElement = document.getElementById("tripsListElement");
        const data = yield response.json();
        const tripList = data;
        for (let i = 0; i < tripList.length; ++i) {
            let link = document.createElement("a");
            link.href = "detail.html?trip_id=" + tripList[i].trip_id.toString();
            let title = document.createElement("h2");
            title.textContent = tripList[i].title;
            let linkDiv = document.createElement("div");
            linkDiv.appendChild(title);
            link.appendChild(linkDiv);
            tripsListElement.appendChild(link);
        }
    });
}
function getTrips() {
    return __awaiter(this, void 0, void 0, function* () {
        const apiUrl = "api/trips";
        const response = yield fetch(apiUrl);
        if (!response.ok) {
            throw new Error("Unable to fetch list of trips");
        }
        yield createList(response);
    });
}
getTrips()
    .then(() => {
    console.log("OK");
})
    .catch((err) => {
    console.error('Error:', err);
});
