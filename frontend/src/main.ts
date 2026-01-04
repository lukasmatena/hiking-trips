
import { currentUser, updateCurrentUserState, loginUsingPassword, logOut} from './auth'

interface TripData {
    trip_id: number;
    title: string;
    date_start: string;
    date_end: string;
}



async function createList(response: Response)
{
    const data = await response.json() as TripData[]
    const tripList: Array<TripData> = data

    let tripsListElement = document.getElementById("tripsListElement") as HTMLDivElement;
    tripsListElement.innerHTML = "";

    let heading = document.createElement("h1") as HTMLHeadingElement;
    heading.textContent = tripList.length != 0 ? "Čundry" : "(nic tu není)";
    tripsListElement.appendChild(heading);    
    
    for (let i=0; i<tripList.length; ++i) {
        let link = document.createElement("a") as HTMLAnchorElement
        link.href = "detail.html?trip_id=" + tripList[i].trip_id.toString()
        let title = document.createElement("h2") as HTMLHeadingElement
        title.textContent = tripList[i].date_start + " " + (tripList[i].title == "" ? "(nepojmenovaný)" : tripList[i].title);
        let linkDiv = document.createElement("div") as HTMLDivElement
        linkDiv.appendChild(title);
        link.appendChild(linkDiv);
        tripsListElement.appendChild(link);
    }
    if (currentUser.role == "admin") {
        const addTripButton = document.createElement("button");
        addTripButton.textContent = "Přidej nový čundr";
        addTripButton.onclick = async () => {
            const url: string = "/api/trips/";
            const token = sessionStorage.getItem('token');
            const reqInit: RequestInit = {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            }
            const response = await fetch(url, reqInit);
            if (! response.ok) {
                console.log(`Add trip request failed`);
            } else {
                window.location.reload();
            }
        };
        
        tripsListElement.appendChild(addTripButton);
    }
}



async function getTrips(): Promise<void>
{
    const token = sessionStorage.getItem('token');
    if (token) {
        const response = await fetch("/api/trips", {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        if (response.ok) {
            await createList(response);
            return;
        }
    }
    let tripsListElement = document.getElementById("tripsListElement") as HTMLDivElement;
    tripsListElement.innerHTML = "";
}





async function updateLoginPanel(): Promise<void>
{
    await updateCurrentUserState();


    const loginElement = document.getElementById("loginElement") as HTMLDivElement;
    loginElement.innerHTML = "";


    if (currentUser.role == "") {
        const loginText = document.createElement("p");
        loginText.textContent = "Zadej heslo:";
        loginElement.appendChild(loginText);
        
        const loginPassword = document.createElement("input");
        loginPassword.setAttribute("type", "password");
        loginElement.appendChild(loginPassword);

        const loginButton = document.createElement("button");
        loginButton.textContent = "Přihlásit se";
        loginElement.appendChild(loginButton);

        loginButton.onclick = async () => {
            const pass: string = loginPassword.value;
            loginButton.textContent = "Zpracovávám...";
            await loginUsingPassword(pass);
            if (currentUser.role == "") {
                window.alert("Chybné heslo!");
            }
            loginPassword.value = "";
            window.location.reload();
        };
        loginPassword.onkeydown = (e) => {
            if (e.key == 'Enter')
                loginButton.click();
        };
    } else {
        const loginButton = document.createElement("button");
        loginButton.textContent = `Odhlásit se (přihlášen jako ${currentUser.role})`;
        loginElement.appendChild(loginButton);

        loginButton.onclick = async () => {
            await logOut();
            window.location.reload();
        };
    }
}


updateLoginPanel()
.then(async ()=>{
    await getTrips();
})
.catch(()=>{});
