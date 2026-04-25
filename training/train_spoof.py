"""
Training script: Fine-tune MobileNetV2 for binary spoof detection.

Dataset folder structure expected:
  training/data/
    real/       ← real face images (.jpg/.png)
    spoof/      ← spoofed images (print, video replay, deepfake)

Usage:
  python training/train_spoof.py --data training/data --epochs 20 --output backend/models/spoof_model.h5
"""
import argparse
import os
import tensorflow as tf
from tensorflow.keras import layers, Model
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing.image import ImageDataGenerator


def build_model(input_shape=(224, 224, 3)) -> Model:
    base = MobileNetV2(input_shape=input_shape, include_top=False, weights='imagenet')
    # Phase 1: freeze base
    base.trainable = False

    x = base.output
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(256, activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(64, activation='relu')(x)
    x = layers.Dropout(0.3)(x)
    out = layers.Dense(1, activation='sigmoid', name='spoof_output')(x)

    model = Model(inputs=base.input, outputs=out)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-4),
        loss='binary_crossentropy',
        metrics=['accuracy', tf.keras.metrics.AUC(name='auc')],
    )
    return model, base


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data',   default='training/data', help='Dataset root dir')
    parser.add_argument('--epochs', default=20, type=int)
    parser.add_argument('--batch',  default=32, type=int)
    parser.add_argument('--output', default='backend/models/spoof_model.h5')
    args = parser.parse_args()

    # ── Data generators ───────────────────────────────────────────────────
    train_gen = ImageDataGenerator(
        rescale=1./255,
        validation_split=0.2,
        rotation_range=15,
        width_shift_range=0.1,
        height_shift_range=0.1,
        horizontal_flip=True,
        brightness_range=[0.8, 1.2],
        zoom_range=0.1,
        shear_range=5,
        fill_mode='reflect',
    )

    train_ds = train_gen.flow_from_directory(
        args.data,
        target_size=(224, 224),
        batch_size=args.batch,
        class_mode='binary',
        subset='training',
        classes=['spoof', 'real'],   # spoof=0, real=1
        shuffle=True,
    )
    val_ds = train_gen.flow_from_directory(
        args.data,
        target_size=(224, 224),
        batch_size=args.batch,
        class_mode='binary',
        subset='validation',
        classes=['spoof', 'real'],
        shuffle=False,
    )

    print(f"Classes: {train_ds.class_indices}")
    print(f"Train: {train_ds.samples} | Val: {val_ds.samples}")

    model, base = build_model()
    model.summary()

    callbacks = [
        tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
        tf.keras.callbacks.ModelCheckpoint(args.output, save_best_only=True),
        tf.keras.callbacks.ReduceLROnPlateau(patience=3, factor=0.5, min_lr=1e-6),
    ]

    # Phase 1: train head only
    print("\n=== Phase 1: Training head layers ===")
    model.fit(train_ds, validation_data=val_ds, epochs=args.epochs // 2, callbacks=callbacks)

    # Phase 2: unfreeze last 30 base layers for fine-tuning
    print("\n=== Phase 2: Fine-tuning ===")
    base.trainable = True
    for layer in base.layers[:-30]:
        layer.trainable = False

    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-5),
        loss='binary_crossentropy',
        metrics=['accuracy', tf.keras.metrics.AUC(name='auc')],
    )
    model.fit(train_ds, validation_data=val_ds, epochs=args.epochs // 2, callbacks=callbacks)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    model.save(args.output)
    print(f"\n✅ Model saved to {args.output}")

    # Evaluate
    loss, acc, auc = model.evaluate(val_ds)
    print(f"Val — Loss: {loss:.4f} | Acc: {acc:.4f} | AUC: {auc:.4f}")


if __name__ == '__main__':
    main()
