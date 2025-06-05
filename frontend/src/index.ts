

interface TripData {
    trip_id: number;
    title: string;
    date_start: string;
    date_end: string;
}


async function createList(response: Response)
{
    let tripsListElement = document.getElementById("tripsListElement") as HTMLDivElement;

    const data = await response.json() as TripData[]
    const tripList: Array<TripData> = data
    for (let i=0; i<tripList.length; ++i) {
        let link = document.createElement("a") as HTMLAnchorElement
        link.href = "detail.html?trip_id=" + tripList[i].trip_id.toString()
        let title = document.createElement("h2") as HTMLHeadingElement
        title.textContent = tripList[i].title

        let linkDiv = document.createElement("div") as HTMLDivElement
        linkDiv.appendChild(title)
        link.appendChild(linkDiv)
        tripsListElement.appendChild(link);
    }
}

async function getTrips(): Promise<void>
{
    const apiUrl = "api/trips"
    const response = await fetch(apiUrl)
    if (! response.ok) {
        throw new Error("Unable to fetch list of trips")
    }
    await createList(response)
}

getTrips()
    .then(() => {
        console.log("OK")
    })
    .catch((err) => {
        console.error('Error:', err);
    });
