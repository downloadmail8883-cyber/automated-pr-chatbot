// Create chatbot container
const chatbot = document.createElement("div");
chatbot.id = "dpib-chatbot";

chatbot.innerHTML = `
  <div id="dpib-header">Data Platform Intake Bot</div>
  <div id="dpib-messages">
    <div class="dpib-bot">
      Hello 👋 How can I help you with your PR's
      Ask me anything!
    </div>
  </div>
  <div id="dpib-input">
    <input type="text" placeholder="Type your message..." />
    <button>Send</button>
  </div>
`;

document.body.appendChild(chatbot);

const input = chatbot.querySelector("input");
const button = chatbot.querySelector("button");
const messages = chatbot.querySelector("#dpib-messages");

function addMessage(text, className) {
  const div = document.createElement("div");
  div.className = className;
  div.innerText = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

button.onclick = async () => {
  const userMessage = input.value.trim();
  if (!userMessage) return;

  addMessage(userMessage, "dpib-user");
  input.value = "";

  try {
    const response = await fetch("http://127.0.0.1:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMessage })
    });

    const data = await response.json();
    addMessage(data.response, "dpib-bot");
  } catch (err) {
    addMessage("⚠️ Backend not reachable.", "dpib-bot");
  }
};
