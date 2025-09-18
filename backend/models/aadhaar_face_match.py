# aadhaar_face_match.py
# Aadhaar Face Verification using Siamese Network
# Requires: tensorflow, mtcnn, sklearn

import os
import random
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, Model, backend as K
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing.image import img_to_array, load_img
from mtcnn import MTCNN
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# ---------- SETTINGS ----------
IMG_SIZE = (160, 160)
EMBED_DIM = 128
BATCH_SIZE = 16
AUTOTUNE = tf.data.AUTOTUNE
# ------------------------------

detector = MTCNN()

# ------------ FACE DETECTION & ALIGNMENT ------------
def detect_and_align(path, target_size=IMG_SIZE):
    img = load_img(path)
    img_arr = img_to_array(img).astype('uint8')
    dets = detector.detect_faces(img_arr)
    if not dets:
        # fallback: center crop + resize
        img_resized = tf.image.resize(img_arr, target_size).numpy()
        return img_resized / 255.0
    best = max(dets, key=lambda d: d['confidence'])
    x, y, w, h = best['box']
    x, y = max(0, x), max(0, y)
    face = img_arr[y:y+h, x:x+w]
    face = tf.image.resize(face, target_size).numpy()
    return face / 255.0

# ------------ DATASET UTILS ------------
def load_image_paths(dataset_root):
    ids = [os.path.join(dataset_root, d) for d in os.listdir(dataset_root) if os.path.isdir(os.path.join(dataset_root, d))]
    id_to_imgs = {}
    for d in ids:
        img_files = [os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(('.jpg', '.png'))]
        if len(img_files) >= 1:
            id_to_imgs[os.path.basename(d)] = img_files
    return id_to_imgs

def make_pairs(id_to_imgs, num_neg_per_pos=1):
    people = list(id_to_imgs.keys())
    pairs = []
    labels = []
    for pid in people:
        imgs = id_to_imgs[pid]
        # positive pairs
        for i in range(len(imgs)):
            for j in range(i+1, len(imgs)):
                pairs.append((imgs[i], imgs[j]))
                labels.append(1)
                # negatives
                for _ in range(num_neg_per_pos):
                    neg_pid = random.choice([p for p in people if p != pid])
                    neg_img = random.choice(id_to_imgs[neg_pid])
                    pairs.append((imgs[i], neg_img))
                    labels.append(0)
    return pairs, labels

# Data generator
def pair_generator(pairs, labels, batch_size=BATCH_SIZE, shuffle=True):
    def gen():
        idx = list(range(len(pairs)))
        if shuffle:
            random.shuffle(idx)
        for i in idx:
            a, b = pairs[i]
            la = detect_and_align(a)
            lb = detect_and_align(b)
            yield la.astype('float32'), lb.astype('float32'), np.float32(labels[i])
    output_types = (tf.float32, tf.float32, tf.float32)
    output_shapes = (IMG_SIZE + (3,), IMG_SIZE + (3,), ())
    ds = tf.data.Dataset.from_generator(gen, output_types=output_types, output_shapes=output_shapes)
    ds = ds.batch(batch_size).prefetch(AUTOTUNE)
    return ds

# ------------ CUSTOM L2 NORMALIZE LAYER ------------
class L2Normalize(layers.Layer):
    def call(self, inputs):
        return tf.nn.l2_normalize(inputs, axis=1)

# ------------ MODEL CREATION ------------
def create_embedding_model(input_shape=IMG_SIZE+(3,), embed_dim=EMBED_DIM):
    base = MobileNetV2(input_shape=input_shape, include_top=False, pooling='avg', weights='imagenet')
    for layer in base.layers[:-30]:
        layer.trainable = False
    inp = layers.Input(shape=input_shape)
    x = base(inp)
    x = layers.Dense(512, activation='relu')(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(embed_dim)(x)
    x = L2Normalize()(x)   # ✅ replaces Lambda
    model = Model(inputs=inp, outputs=x, name='embedding_model')
    return model

def build_siamese(embedding_model):
    input_a = layers.Input(shape=IMG_SIZE+(3,))
    input_b = layers.Input(shape=IMG_SIZE+(3,))
    emb_a = embedding_model(input_a)
    emb_b = embedding_model(input_b)

    def euclidean_distance(vects):
        x, y = vects
        return K.sqrt(K.maximum(K.sum(K.square(x - y), axis=1, keepdims=True), K.epsilon()))

    def euclidean_output_shape(shapes):
        return (shapes[0][0], 1)

    distance = layers.Lambda(euclidean_distance, output_shape=euclidean_output_shape)([emb_a, emb_b])
    model = Model([input_a, input_b], distance)
    return model

# ------------ LOSS ------------
def contrastive_loss(margin=1.0):
    def loss(y_true, y_pred):
        y_true = tf.cast(y_true, y_pred.dtype)
        square_pred = tf.square(y_pred)
        margin_square = tf.square(tf.maximum(margin - y_pred, 0.0))
        return tf.reduce_mean(y_true * square_pred + (1.0 - y_true) * margin_square)
    return loss

# ------------ TRAINING ------------
def train(dataset_root, epochs=10):
    id_to_imgs = load_image_paths(dataset_root)
    pairs, labels = make_pairs(id_to_imgs, num_neg_per_pos=1)
    train_pairs, val_pairs, train_labels, val_labels = train_test_split(
        pairs, labels, test_size=0.12, random_state=42
    )
    train_ds = pair_generator(train_pairs, train_labels, batch_size=BATCH_SIZE)
    val_ds = pair_generator(val_pairs, val_labels, batch_size=BATCH_SIZE, shuffle=False)

    emb_model = create_embedding_model()
    siamese = build_siamese(emb_model)
    siamese.compile(optimizer=tf.keras.optimizers.Adam(1e-4),
                    loss=contrastive_loss(margin=1.0))

    def map_ds(ds):
        return ds.map(lambda a, b, l: ((a, b), l))

    train_ds_mapped = map_ds(train_ds).repeat()
    val_ds_mapped = map_ds(val_ds).repeat()

    steps_per_epoch = max(1, len(train_pairs) // BATCH_SIZE)
    val_steps = max(1, len(val_pairs) // BATCH_SIZE)

    siamese.fit(
        train_ds_mapped,
        validation_data=val_ds_mapped,
        epochs=epochs,
        steps_per_epoch=steps_per_epoch,
        validation_steps=val_steps
    )

    # ✅ Save in both formats
    siamese.save('best_siamese.keras')
    siamese.save('best_siamese.h5')
    emb_model.save('face_embedding_model.h5')

    return emb_model, val_pairs, val_labels

# ------------ INFERENCE ------------
def infer(embedding_model, img_path_a, img_path_b, threshold=0.7):
    a = detect_and_align(img_path_a)
    b = detect_and_align(img_path_b)
    a = np.expand_dims(a.astype('float32'), axis=0)
    b = np.expand_dims(b.astype('float32'), axis=0)
    ea = embedding_model.predict(a)
    eb = embedding_model.predict(b)
    dist = np.linalg.norm(ea - eb)
    match = dist < threshold
    return float(dist), bool(match)

# ------------ AUTO-THRESHOLD FINDER ------------
def find_best_threshold(embedding_model, val_pairs, val_labels, thresholds=np.linspace(0.4, 0.8, 9)):
    """
    Finds the best threshold automatically based on validation accuracy.
    """
    best_th = None
    best_acc = -1
    for th in thresholds:
        preds = []
        for (a, b), label in zip(val_pairs, val_labels):
            d, m = infer(embedding_model, a, b, threshold=th)
            preds.append(int(m))
        acc = accuracy_score(val_labels, preds)
        if acc > best_acc:
            best_acc = acc
            best_th = th
    print(f"\n✅ Best threshold found: {best_th:.2f} with accuracy {best_acc:.4f}")
    return best_th

# ------------ MAIN ------------
if __name__ == '__main__':
    dataset_root = r"C:\Users\Rushyanth\Downloads\dataset_root"
    emb_model, val_pairs, val_labels = train(dataset_root, epochs=8)

    # ✅ Automatically pick best threshold
    best_th = find_best_threshold(emb_model, val_pairs, val_labels)

    # Example test
    test_aadhar = r"C:\Users\Rushyanth\Downloads\dataset_root\person1\aadhar.jpg"
    test_live = r"C:\Users\Rushyanth\Downloads\dataset_root\person1\live1.jpg"
    dist, match = infer(emb_model, test_aadhar, test_live, threshold=best_th)
    print(f"\nDistance: {dist:.4f} | Match? {match}")
