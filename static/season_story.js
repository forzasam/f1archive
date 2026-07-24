const storyModal = document.querySelector("[data-story-modal]");
const storyOpen = document.querySelector("[data-story-open]");
const storyCloseButtons = document.querySelectorAll("[data-story-close]");
let storyReturnFocus = null;

function openStory() {
    if (!storyModal) return;
    storyReturnFocus = document.activeElement;
    storyModal.hidden = false;
    document.body.classList.add("story-modal-open");
    storyModal.querySelector(".story-modal-close")?.focus();
}

function closeStory() {
    if (!storyModal) return;
    storyModal.hidden = true;
    document.body.classList.remove("story-modal-open");
    storyReturnFocus?.focus();
}

storyOpen?.addEventListener("click", openStory);
storyCloseButtons.forEach((button) => button.addEventListener("click", closeStory));

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && storyModal && !storyModal.hidden) closeStory();
});
