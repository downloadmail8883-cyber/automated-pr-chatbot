console.log("✅ Data Platform Intake Bot injected");

// ---- Create chatbot container ----
const chatbot = document.createElement("div");
chatbot.id = "dpib-chatbot";

chatbot.innerHTML = `
  <div id="dpib-header">Data Platform Intake Bot</div>
  <div id="dpib-messages">
    <div class="dpib-bot">
      👋 Hi! I can help you create automated PRs.
      <br /><br />
      Try saying: <b>Create a Glue Database PR</b>
    </div>
  </div>
  <div id="dpib-input">
    <input type="text" placeholder="Type your message..." />
    <button>Send</button>
  </div>
`;

// ---- Append to page ----
document.body.appendChild(chatbot);

// ---- Chat logic ----
const input = chatbot.querySelector("input");
const button = chatbot.querySelector("button");
const messages = chatbot.querySelector("#dpib-messages");

let conversation = [];

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
  conversation.push({ role: "user", content: userMessage });
  input.value = "";

  try {
    const response = await fetch("http://127.0.0.1:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: conversation }),
    });

    const data = await response.json();
    addMessage(data.response, "dpib-bot");
    conversation.push({ role: "assistant", content: data.response });
  } catch (err) {
    addMessage("⚠️ Backend not reachable", "dpib-bot");
  }
};
