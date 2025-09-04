from PIL import Image

# Open the uploaded image
img_path = r"C:\Users\siri\Downloads\generated-image (2).png"
img = Image.open(img_path)

# Resize the image to 1920x160 (12:1 ratio)
resized_img = img.resize((1920, 160))

# Save the resized image
output_path = r"C:\Users\siri\Downloads\resized_advertisement.png"
resized_img.save(output_path)

output_path
