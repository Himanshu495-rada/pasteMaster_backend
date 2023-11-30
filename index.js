const express = require("express");
const bodyParser = require("body-parser");
const { nanoid } = require("nanoid");
const cors = require("cors");
const { PrismaClient } = require("@prisma/client");

const prisma = new PrismaClient();
const app = express();

app.use(cors());
app.use(bodyParser.json());

const textStore = {};

// Function to remove text based on code
const removeText = async (code) => {
  await prisma.textData.delete({
    where: { code },
  });
  console.log(`Text with code ${code} removed from the database.`);
};

app.get("/", (req, res) => {
  res.send("Working");
});

app.post("/store", async (req, res) => {
  const { text } = req.body;
  const code = nanoid(4);

  // Store text in the database
  await prisma.textData.create({
    data: {
      code,
      text,
      timestamp: new Date(),
    },
  });

  res.json({ code });
});

app.get("/retrieve/:code", async (req, res) => {
  const { code } = req.params;

  const storedText = await prisma.textData.findUnique({
    where: { code },
  });

  if (storedText) {
    await removeText(code);
    res.json({ text: storedText.text });
  } else {
    res.status(404).json({ error: "Code not found" });
  }
});

setInterval(async () => {
  const currentTime = new Date();
  const expirationDuration = 10 * 60 * 1000; // 10 minutes

  const oldEntries = await prisma.textData.findMany({
    where: {
      timestamp: {
        lt: new Date(currentTime - expirationDuration),
      },
    },
  });

  // Remove old entries
  await Promise.all(oldEntries.map((entry) => removeText(entry.code)));
}, 10 * 60 * 1000);

app.listen(3000, () => {
  console.log(`Server is running on http://localhost:${3000}`);
});
