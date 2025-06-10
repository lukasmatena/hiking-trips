interface TripDetail {
    trip_id: number;
    title: string;
    description: string;
    date_start: string;
    date_end: string;
    urls: string[];
    prev_trip_id: number | null;
    next_trip_id: number | null;
}


async function createPage(tripDetail: TripDetail)
{
    let title = document.getElementById("titleElement") as HTMLHeadingElement
    let desc = document.getElementById("descriptionElement") as HTMLHeadingElement
    let prev = document.getElementById("prevTripElement") as HTMLAnchorElement
    let next = document.getElementById("nextTripElement") as HTMLAnchorElement
    title.textContent = tripDetail.title
    desc.textContent = tripDetail.description

    prev.href = tripDetail.prev_trip_id ? "detail.html?trip_id=" + tripDetail.prev_trip_id.toString() : ""
    next.href = tripDetail.next_trip_id ? "detail.html?trip_id=" + tripDetail.next_trip_id.toString() : ""

    let photosElement = document.getElementById("photosElement") as HTMLDivElement
    const photoUrls: string[] = tripDetail.urls
    for (let i=0; i<photoUrls.length; ++i) {
        const photoTitleText: string = "photo number " + i.toString()
        const photoUrl: string = photoUrls[i]
        let photoLink = document.createElement("a") as HTMLAnchorElement
        let photoImage = document.createElement("img") as HTMLImageElement
        photoImage.src = photoUrl
        photoImage.title = photoTitleText
        photoImage.alt = photoTitleText
        photoLink.href = photoUrl
        let brElement = document.createElement("br") as HTMLBRElement
        photoLink.appendChild(photoImage)
        photosElement.appendChild(photoLink)
        photosElement.appendChild(brElement)
    }
}


async function readTripData(trip_id: number)
{
    const apiUrl = "api/trips/" + trip_id.toString()
    const response = await fetch(apiUrl)
    if (! response.ok)
        throw new Error("Error fetching data (" + response.status.toString() + ": " + response.statusText)
    return response
}

function loadTrip(trip_id: number): void
{
    readTripData(trip_id)
        .then(async (tripDetail: Response) => {
            await createPage(await tripDetail.json())
        })
        .catch((error) => {
            console.log(error)
        })
}

function parseTripId(): number
{
    const queryStr = window.location.search
    const params = new URLSearchParams(queryStr)

    const trip_str = params.get("trip_id")
    if (trip_str == null)
        throw new Error("Invalid trip number")
    const trip_id = parseInt(trip_str, 10)
    if (isNaN(trip_id))
        throw new Error("Invalid trip number")
    return trip_id
}


try {
    const trip_id = parseTripId()
    loadTrip(trip_id)
} catch (error) {
    console.log(error)
}
