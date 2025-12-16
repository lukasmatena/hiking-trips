interface CurrentUser {
    role: string
}

export let currentUser: CurrentUser = { role: ""};

export async function updateCurrentUserState() : Promise<void>
{
    currentUser.role = "";
    const token = sessionStorage.getItem("token")
    if (token) {
        const response = await fetch("api/me", {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        })
        if (response.ok)
            currentUser.role = await response.text();
    }
}



export async function loginUsingPassword(pass: string): Promise<void>
{
    const apiUrl = "api/login";

    const body = new URLSearchParams();
    body.append('username', "dummyusername");
    body.append('password', pass);

    const response = await fetch(apiUrl, {
        method: 'POST',
        body: body
    });
    if (response.ok) {
        const data = JSON.parse(await response.text());
        if (data.access_token.length != 0)
                sessionStorage.setItem("token", data.access_token)
            else
                sessionStorage.removeItem("token");
    }
    await updateCurrentUserState();    
}



export async function logOut()
{
    sessionStorage.removeItem("token");
    await updateCurrentUserState();
}
