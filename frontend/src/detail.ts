import { currentUser, updateCurrentUserState } from "./auth";

interface PhotoData {
    photo_id: number;
    url: string;
}

interface TripBasicData {
    trip_id: number;
    title: string;
    date_start: string;
    date_end: string;
}

interface TripDetail extends TripBasicData{
    description: string;
    photos: PhotoData[];
    prev_trip_id: number | null;
    next_trip_id: number | null;
}

interface TripUpdateData  extends TripBasicData{
    desc: string;
    photos_to_delete: number[];
}

async function confirm_edits(tripData: TripDetail): Promise<void>
{
    const editTitleElement = document.getElementById("editTitleElement") as HTMLInputElement
    const editDescElement = document.getElementById("editDescElement") as HTMLTextAreaElement
    const editStartElement = document.getElementById("editStartElement") as HTMLInputElement
    const editEndElement = document.getElementById("editEndElement") as HTMLInputElement

    let photosToDelete: number[] = []
    const images = document.getElementsByTagName("input")
    for (let image of images) {
        const prefix: string = "checkbox_for_photo_"
        if (image.id.startsWith(prefix)) {
            if (! image.checked) {
                const num_str = image.id.slice(prefix.length)
                photosToDelete.push(parseInt(num_str))
            }
        }
    }

    const tripUpdateData: TripUpdateData = {
        trip_id: tripData.trip_id,
        title: editTitleElement.value,
        desc: editDescElement.value,
        date_start: editStartElement.value,
        date_end: editEndElement.value,
        photos_to_delete: photosToDelete
    }

    const formData = new FormData();
    formData.append('updated_trip_json', JSON.stringify(tripUpdateData));

    const editFilesDiv = document.getElementById("editFilesDiv") as HTMLDivElement;
    const filePickers = editFilesDiv.querySelectorAll('input[type="file"]');
    for (const filePicker_ of filePickers) {
        const filePicker = filePicker_ as HTMLInputElement;
        if (filePicker.files && filePicker.files.length > 0) {
            for (const file of filePicker.files) {
                formData.append('files', file);
            }
        }
    }

    const token = sessionStorage.getItem('token');
    let response: Response = await fetch("/api/trips/" + tripUpdateData.trip_id.toString(), {
        method: "PUT",
        body: formData,
        headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
        window.location.href = "index.html"
    } else {
        console.error("Failed to update trip:", await response.text());
    }
}

function append_new_br(div: HTMLDivElement): void
{
    // TODO: This should better be done using CSS.
    let brElement = document.createElement("br") as HTMLBRElement
    div.appendChild(brElement)
}

function update_file_pickers(): void
{
    let editFilesDiv = document.getElementById("editFilesDiv") as HTMLDivElement
    const filePickers = editFilesDiv.querySelectorAll("input")
    let seenEmpty = false
    for (const filePicker of filePickers) {
        if (filePicker.files && filePicker.files.length == 0)
            seenEmpty = true
    }
    if (! seenEmpty) {
        let new_fp = document.createElement("input") as HTMLInputElement
        new_fp.type = "file"
        new_fp.addEventListener("input", () => { update_file_pickers(); });
        editFilesDiv.appendChild(new_fp)
    }
}

async function createPage(tripDetail: TripDetail, editingMode: boolean)
{
    let contentElement = document.getElementById("contentElement") as HTMLDivElement
    contentElement.innerHTML = ""

    let photosElement = document.createElement("div") as HTMLDivElement
    photosElement.style.display = "flex";
    photosElement.style.flexDirection = "column";
    photosElement.style.alignItems = editingMode ? "left" : "center";
    photosElement.style.gap = editingMode ? "0" : "20px";
    photosElement.style.width = editingMode ? "100px" : "100%";

    const videoRegex = new RegExp("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.[mM][pP]4");

    const photoData: PhotoData[] = tripDetail.photos
    for (let i=0; i<photoData.length; ++i) {
        const photoTitleText: string = "photo number " + i.toString()
        const photoUrl: string = photoData[i].url
        const photoId: number = photoData[i].photo_id
        let photoImage : HTMLImageElement | HTMLVideoElement;
        if (videoRegex.test(photoUrl)) {
            const video = document.createElement("video") as HTMLVideoElement;    
            video.controls = true;
            video.playsInline = true;
            video.muted = true;
            video.preload = "metadata";
            const source = document.createElement("source");
            source.src = photoUrl;
            source.type = "video/mp4";
            video.appendChild(source);
            video.load();
            photoImage = video;
        } else {
            photoImage = document.createElement("img") as HTMLImageElement
            photoImage.alt = photoTitleText
        }
        photoImage.src = photoUrl
        photoImage.title = photoTitleText

        photoImage.style.width = "100%";
        photoImage.style.height = "auto";
        photoImage.style.borderRadius = "8px";

        photosElement.appendChild(photoImage)
        if (editingMode) {
            let checkboxElement = document.createElement("input") as HTMLInputElement
            checkboxElement.type = "checkbox"
            checkboxElement.checked = true
            checkboxElement.id = "checkbox_for_photo_" + photoId.toString()
            photosElement.appendChild(checkboxElement)
            append_new_br(photosElement)
            append_new_br(photosElement)
        }
    }

    if (! editingMode) {
        let title = document.createElement("h1") as HTMLHeadingElement
        let desc = document.createElement("p") as HTMLParagraphElement
        let prev = document.createElement("a") as HTMLAnchorElement
        let next = document.createElement("a") as HTMLAnchorElement
        let index = document.createElement("a") as HTMLAnchorElement

        title.textContent = tripDetail.title
        desc.textContent = tripDetail.description
        desc.style.whiteSpace = "pre-wrap";
        prev.href = tripDetail.prev_trip_id ? "detail.html?trip_id=" + tripDetail.prev_trip_id.toString() : ""
        next.href = tripDetail.next_trip_id ? "detail.html?trip_id=" + tripDetail.next_trip_id.toString() : ""
        index.href = "index.html"
        prev.textContent = "předchozí"
        next.textContent = "další"
        index.textContent = "zpátky na seznam"

        contentElement.appendChild(prev)
        contentElement.appendChild(index)
        contentElement.appendChild(next)
        contentElement.appendChild(title)
        contentElement.appendChild(desc)
        contentElement.appendChild(photosElement)

        if (currentUser.role == "admin") {
            let buttonMode = document.createElement("button") as HTMLButtonElement
            buttonMode.textContent = "Editovat"
            buttonMode.onclick = async () => {
                createPage(tripDetail, true)
            };
            contentElement.appendChild(buttonMode)
        }
    } else {
        // Editing mode:
        let editTitleElement = document.createElement("input") as HTMLInputElement
        editTitleElement.value = tripDetail.title
        editTitleElement.id = "editTitleElement"
        contentElement.appendChild(editTitleElement)
        append_new_br(contentElement)

        let editDescElement = document.createElement("textarea") as HTMLTextAreaElement
        editDescElement.value = tripDetail.description
        editDescElement.id = "editDescElement"
        contentElement.appendChild(editDescElement)
        append_new_br(contentElement)

        let editStartElement = document.createElement("input") as HTMLInputElement
        editStartElement.type = "date"
        editStartElement.id = "editStartElement"
        editStartElement.value = tripDetail.date_start
        contentElement.appendChild(editStartElement)
        append_new_br(contentElement)

        let editEndElement = document.createElement("input") as HTMLInputElement
        editEndElement.type = "date"
        editEndElement.id = "editEndElement"
        editEndElement.value = tripDetail.date_end
        contentElement.appendChild(editEndElement)
        append_new_br(contentElement)

        contentElement.appendChild(photosElement)

        let editFilesDiv = document.createElement("div") as HTMLDivElement
        editFilesDiv.id = "editFilesDiv"
        let editFileElement = document.createElement("input") as HTMLInputElement
        editFileElement.type = "file"
        editFileElement.id = "editFileElement_0"
        editFileElement.addEventListener("input", () => { update_file_pickers(); })
        editFilesDiv.appendChild(editFileElement)
        contentElement.appendChild(editFilesDiv)
        append_new_br(contentElement)

        let buttonDelete = document.createElement("button") as HTMLButtonElement
        buttonDelete.id = "buttonDelete"
        buttonDelete.addEventListener("click", async () => {
            if (window.confirm("Určitě chceš čundr smazat?")) {
                const apiUrl = "/api/trips/" + tripDetail.trip_id.toString()
                const token = sessionStorage.getItem('token');
                const response = await fetch(apiUrl, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${token}` }
                })
                if (! response.ok)
                    console.log("Deleting trip failed");
                else
                    window.location.href = "index.html"
            }
        })
        buttonDelete.textContent = "SMAZAT"
        contentElement.appendChild(buttonDelete)

        let buttonConfirm = document.createElement("button") as HTMLButtonElement
        buttonConfirm.id = "buttonConfirm"
        buttonConfirm.addEventListener("click", () => { confirm_edits(tripDetail); })
        buttonConfirm.textContent = "Potvrdit"
        contentElement.appendChild(buttonConfirm)
    }
}


async function readTripData(trip_id: number)
{
    const token = sessionStorage.getItem('token');
    const response = await fetch("/api/trips/" + trip_id.toString(), {
        headers: { 'Authorization': `Bearer ${token}` }
    })
    if (! response.ok)
        throw new Error("Error fetching data (" + response.status.toString() + ": " + response.statusText)
    return response
}

function loadTrip(trip_id: number): void
{
    readTripData(trip_id)
        .then(async (tripDetail: Response) => {
            await createPage(await tripDetail.json(), false)
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



updateCurrentUserState()
.then(async() => {
    const trip_id = parseTripId()
    loadTrip(trip_id)
})
.catch((error)=>{ console.log(error) });
