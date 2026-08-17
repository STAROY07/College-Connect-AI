const input = document.getElementById("user-input");
const sendButton = document.getElementById("send-button");
const messages = document.querySelector(".messages");


sendButton.addEventListener("click", async function () {

    const userMessage = input.value.trim();

    if (userMessage === "") {
        return;
    }

    const userBubble = document.createElement("div");
    userBubble.className = "user-message";
    userBubble.textContent = userMessage;

    messages.appendChild(userBubble);

    input.value = "";


    const response = await fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            message: userMessage
        })
    });


    const data = await response.json();

    const botBubble = document.createElement("div");
    botBubble.className = "bot-message";
    botBubble.textContent = data.reply;

    messages.appendChild(botBubble);
});

input.addEventListener("keypress", function (event) {
    if (event.key === "Enter") {
        sendButton.click();
    }
});