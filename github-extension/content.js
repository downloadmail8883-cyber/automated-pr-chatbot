// Content script for MIW Data Platform Assistant Chrome Extension
// Injects chatbot UI into GitHub pages

const API_URL = "http://localhost:8000"; // Change to your backend URL
let sessionId = `session-${Date.now()}`;
let conversationHistory = [];

// Create chatbot UI
function createChatbotUI() {
  const container = document.createElement("div");
  container.id = "miw-chatbot-container";
  container.innerHTML = `
    <div id="miw-chatbot-header">
      <span>🤖 MIW Data Platform Assistant</span>
      <button id="miw-chatbot-minimize">−</button>
    </div>
    <div id="miw-chatbot-messages"></div>
    <div id="miw-chatbot-input-area">
      <textarea id="miw-chatbot-input" placeholder="Type your message..."></textarea>
      <button id="miw-chatbot-send">Send</button>
    </div>
    <div id="miw-chatbot-reset">
      <button id="miw-reset-button">🔄 Reset Session</button>
    </div>
  `;

  document.body.appendChild(container);

  // Event listeners
  document.getElementById("miw-chatbot-send").addEventListener("click", sendMessage);
  document.getElementById("miw-chatbot-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  document.getElementById("miw-chatbot-minimize").addEventListener("click", () => {
    const container = document.getElementById("miw-chatbot-container");
    container.classList.toggle("minimized");
  });

  document.getElementById("miw-reset-button").addEventListener("click", resetSession);

  // Initial greeting
  addBotMessage("👋 Hey there! I'm your MIW Data Platform Assistant!\n\nI help you create automated Pull Requests for:\n✨ **Glue Databases**\n✨ **S3 Buckets**\n✨ **IAM Roles**\n\nWhat would you like to create today?");
}

// Add message to chat
function addMessage(message, isUser = false) {
  const messagesDiv = document.getElementById("miw-chatbot-messages");
  const messageDiv = document.createElement("div");
  messageDiv.className = `miw-message ${isUser ? "user" : "bot"}`;

  // Convert markdown-style formatting
  const formattedMessage = message
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');

  messageDiv.innerHTML = formattedMessage;
  messagesDiv.appendChild(messageDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addBotMessage(message) {
  addMessage(message, false);
}

function addUserMessage(message) {
  addMessage(message, true);
}

// Send message to backend
async function sendMessage() {
  const input = document.getElementById("miw-chatbot-input");
  const userMessage = input.value.trim();

  if (!userMessage) return;

  addUserMessage(userMessage);
  input.value = "";

  conversationHistory.push({ role: "user", content: userMessage });

  // Show typing indicator
  const typingDiv = document.createElement("div");
  typingDiv.id = "typing-indicator";
  typingDiv.className = "miw-message bot";
  typingDiv.innerHTML = "<em>Typing...</em>";
  document.getElementById("miw-chatbot-messages").appendChild(typingDiv);

  try {
    const response = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: conversationHistory,
        session_id: sessionId
      })
    });

    // Remove typing indicator
    const indicator = document.getElementById("typing-indicator");
    if (indicator) indicator.remove();

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();

    conversationHistory.push({ role: "assistant", content: data.response });
    addBotMessage(data.response);

  } catch (error) {
    // Remove typing indicator
    const indicator = document.getElementById("typing-indicator");
    if (indicator) indicator.remove();

    addBotMessage(`❌ Error: ${error.message}\n\nPlease make sure the backend is running at ${API_URL}`);
  }
}

// Reset session
async function resetSession() {
  try {
    await fetch(`${API_URL}/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId })
    });

    // Clear UI
    document.getElementById("miw-chatbot-messages").innerHTML = "";
    conversationHistory = [];
    sessionId = `session-${Date.now()}`;

    addBotMessage("✅ Session reset! What would you like to create?");
  } catch (error) {
    addBotMessage(`❌ Reset failed: ${error.message}`);
  }
}

// Initialize when page loads
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", createChatbotUI);
} else {
  createChatbotUI();
}